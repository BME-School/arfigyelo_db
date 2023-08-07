from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re
import webscrape_util
import sqlite3
import time
import threading
import mysql.connector


db_config = {
    "host": "localhost",
    "user": "admin",
    "password": "admin",
    "database": "arfigyelo"
}

mysql_conn = mysql.connector.connect(**db_config)
mysql_cursor = mysql_conn.cursor()


def update_mysql_row(market, sku, value, img=""):
    mysql_cursor.execute(f"SELECT * FROM products WHERE {market}=?", (sku,))
    result = mysql_cursor.fetchone()
    if result:
        if img:
            mysql_cursor.execute(f"UPDATE products SET {market}_price = ?, img = ? WHERE {market}=?", (value, sku, img))
        else:
            mysql_cursor.execute(f"UPDATE products SET {market}_price = ? WHERE {market}=?", (value, sku))
        mysql_conn.commit()


options = Options()
# options.add_argument("--headless")
options.add_experimental_option("prefs", {"profile.managed_default_content_settings.images": 2})
options.add_argument("--disable-dev-shm-usage")


# Visszaadja az első "xxx Ft" formátumű szövegből az árat egész számként
def get_first_price(txt):
    match = re.search(r'\b([\d\s.,]+) Ft\b', txt)
    return int(float(match.group(1).replace(",", "").replace(" ", ""))) if match else 0


# aldi
# def get_all_price_aldi():
#     category = webscrape_util.get_category_aldi()
#     conn = sqlite3.connect('adatbazis_aldi.db')
#     c = conn.cursor()
#     driver = webdriver.Chrome(options=options)
#
#     for cg in category:
#         driver.get(cg)
#         try:
#             category_name = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, "h1"))).text
#         except TimeoutException:
#             print(cg)
#             category.append(cg)
#             continue
#
#
#         products_sql = []
#         prices_sql = []
#         while True:
#             original_url = driver.current_url
#             driver.find_element(By.TAG_NAME, "body").send_keys(Keys.END)
#             time.sleep(1)
#             if driver.current_url == original_url:
#                 time.sleep(1)
#                 driver.find_element(By.TAG_NAME, "body").send_keys(Keys.END)
#                 time.sleep(1)
#                 if driver.current_url == original_url:
#                     break
#
#         products_sql = []
#         prices_sql = []
#
#         products = driver.find_elements(By.CLASS_NAME, "product-card-cotainer-w")
#         for p in products:
#             element = p.find_element(By.CLASS_NAME, "product-card-text").find_element(By.CLASS_NAME, "product-card-image-link")
#             name = element.find_element(By.CSS_SELECTOR, "span").get_attribute("innerHTML")
#             sku = element.get_attribute("href").split("/")[-1]
#             products_sql.append((sku, category_name, name, sku))
#
#             price = p.find_element(By.CSS_SELECTOR, 'span[itemprop="price"]').text
#             price = ''.join(filter(str.isdigit, price))
#             try:
#                 old_price = p.find_element(By.CLASS_NAME, "old-price-container").find_element(By.CSS_SELECTOR, "span")
#                 try:
#                     old_price = get_first_price(old_price.text.replace("\u202f", ""))
#                 except ValueError:
#                     print(old_price.text)
#                 discount_price = price if old_price == 0 else old_price
#             except NoSuchElementException:
#                 discount_price = price
#             prices_sql.append((price, discount_price, sku))
#
#         insert_products = "INSERT INTO products (sku, category, name) SELECT ?, ?, ? WHERE NOT EXISTS (SELECT 1 FROM products WHERE sku = ?)"
#         insert_prices = "INSERT INTO prices (normal_price, discount_price, product_sku) VALUES (?, ?, ?)"
#         c.executemany(insert_products, products_sql)
#         c.executemany(insert_prices, prices_sql)
#         conn.commit()
#
#     driver.quit()
#     conn.close()


# Auchan


def get_all_price_auchan():
    def gorgetes():
        current_position = driver.execute_script("return window.pageYOffset;")
        new_position = current_position + 440
        driver.execute_script(f"window.scrollTo(0, {new_position});")
        time.sleep(2)
    category = webscrape_util.get_category_auchan()
    conn = sqlite3.connect('adatbazis_auchan.db')
    c = conn.cursor()
    driver = webdriver.Chrome(options=options)
    driver.maximize_window()

    for cg in category:
        category_name = cg[1]
        driver.get(cg[0])

        time.sleep(1)
        driver.execute_script(f"window.scrollTo(0, 350)")

        products_sql = []
        prices_sql = []
        mysql_append = []
        termek_db = driver.find_element(By.CLASS_NAME, "_3MDHKZWk").get_attribute("innerHTML").split(" ")[5]
        for i in range(int(float(termek_db)/5)):
            products = driver.find_elements(By.CLASS_NAME, "_390_dcu3")
            for j in range(5):
                try:
                    name_element = products[i * 5 + j].find_element(By.CLASS_NAME, "_1DGZmbHT")
                    price = products[i * 5 + j].find_element(By.CLASS_NAME, "_1-UBPrOw").get_attribute("innerHTML")
                except IndexError:
                    break
                except NoSuchElementException:
                    time.sleep(2)
                    name_element = products[i * 5 + j].find_element(By.CLASS_NAME, "_1DGZmbHT")
                    price = products[i * 5 + j].find_element(By.CLASS_NAME, "_1-UBPrOw").get_attribute("innerHTML")

                name = name_element.find_element(By.CSS_SELECTOR, "span").text
                sku = name_element.get_attribute("href").split("/")[-1]

                try:
                    new_price = products[i * 5 + j].find_element(By.CLASS_NAME, "_1xU8lBe6").get_attribute("innerHTML")
                    discount_price = price
                    price = new_price
                except NoSuchElementException:
                    discount_price = price
                price = ''.join(filter(str.isdigit, price))
                discount_price = ''.join(filter(str.isdigit, discount_price))

                products_sql.append((sku, category_name, name, sku))
                prices_sql.append((price, discount_price, sku))
                mysql_append.append([sku, discount_price])
            gorgetes()
        insert_products = "INSERT INTO products (sku, category, name) SELECT ?, ?, ? WHERE NOT EXISTS (SELECT 1 FROM products WHERE sku = ?)"
        insert_prices = "INSERT INTO prices (normal_price, discount_price, product_sku) VALUES (?, ?, ?)"
        c.executemany(insert_products, products_sql)
        c.executemany(insert_prices, prices_sql)
        for e in mysql_append:
            update_mysql_row("auchan", e[0], e[1])
        conn.commit()

    driver.quit()
    conn.close()


def get_all_price_tesco():
    category = webscrape_util.get_category_tesco()
    conn = sqlite3.connect('adatbazis_tesco.db')
    c = conn.cursor()
    for cg in category:
        i = 1
        category_name = cg.split("/")[6]
        while True:
            driver = webdriver.Chrome(options=options)
            driver.get(cg+f"&page={i}&count=48")
            i += 1

            products = driver.find_elements(By.CLASS_NAME, "product-details--wrapper")
            if len(products) == 0:
                break
            products_sql = []
            prices_sql = []
            mysql_append = []
            for p in products:
                element = p.find_element(By.CSS_SELECTOR, "h3 a")
                sku = element.get_attribute("href").split("/")[-1]
                name = p.find_element(By.CSS_SELECTOR, "h3 span").get_attribute("innerHTML")
                image = p.find_element(By.CSS_SELECTOR, ".product-image").get_attribute("src")
                products_sql.append((sku, category_name, name, sku))
                try:
                    price = get_first_price(p.find_element(By.CLASS_NAME, "beans-price__text").text)
                    discount = p.find_elements(By.CLASS_NAME, "offer-text")
                except NoSuchElementException:
                    continue
                clubcard_price = get_first_price(discount[0].text) if len(discount) > 0 else price
                clubcard_price = price if clubcard_price == 0 else clubcard_price

                prices_sql.append((price, clubcard_price, sku))
                mysql_append.append([sku, clubcard_price, img])

            insert_products = "INSERT INTO products (sku, category, name) SELECT ?, ?, ? WHERE NOT EXISTS (SELECT 1 FROM products WHERE sku = ?)"
            insert_prices = "INSERT INTO prices (normal_price, discount_price, product_sku) VALUES (?, ?, ?)"
            c.executemany(insert_products, products_sql)
            c.executemany(insert_prices, prices_sql)
            for e in mysql_append:
                update_mysql_row("tesco", e[0], e[1], e[2])
            conn.commit()
            driver.quit()
    conn.close()

# penny
# def get_all_price_penny():
#     category = webscrape_util.get_category_penny()
#     conn = sqlite3.connect('adatbazis_penny.db')
#     c = conn.cursor()
#     driver = webdriver.Chrome(options=options)
#
#     for cg in category:
#         driver.get(cg)
#         try:
#             category_name = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, "h1"))).text
#         except TimeoutException:
#             print(cg)
#             category.append(cg)
#             continue
#
#         while True:
#             original_url = driver.current_url
#             driver.find_element(By.TAG_NAME, "body").send_keys(Keys.END)
#             time.sleep(1)
#             if driver.current_url == original_url:
#                 time.sleep(1)
#                 driver.find_element(By.TAG_NAME, "body").send_keys(Keys.END)
#                 time.sleep(1)
#                 if driver.current_url == original_url:
#                     break
#
#         products_sql = []
#         prices_sql = []
#
#         products = driver.find_elements(By.CLASS_NAME, "product-card")
#         for p in products:
#             element = p.find_element(By.CLASS_NAME, "product-card-text").find_element(By.CLASS_NAME, "product-card-image-link")
#             name = element.find_element(By.CSS_SELECTOR, "span").get_attribute("innerHTML")
#             sku = element.get_attribute("href").split("/")[-1]
#             products_sql.append((sku, category_name, name, sku))
#
#             price = p.find_element(By.CSS_SELECTOR, 'span[itemprop="price"]').text
#             price = ''.join(filter(str.isdigit, price))
#             try:
#                 old_price = p.find_element(By.CLASS_NAME, "old-price-container").find_element(By.CSS_SELECTOR, "span")
#                 try:
#                     old_price = get_first_price(old_price.text.replace("\u202f", ""))
#                 except ValueError:
#                     print(old_price.text)
#                 discount_price = price if old_price == 0 else old_price
#             except NoSuchElementException:
#                 discount_price = price
#             prices_sql.append((price, discount_price, sku))
#
#         insert_products = "INSERT INTO products (sku, category, name) SELECT ?, ?, ? WHERE NOT EXISTS (SELECT 1 FROM products WHERE sku = ?)"
#         insert_prices = "INSERT INTO prices (normal_price, discount_price, product_sku) VALUES (?, ?, ?)"
#         c.executemany(insert_products, products_sql)
#         c.executemany(insert_prices, prices_sql)
#         conn.commit()
#
#     driver.quit()
#     conn.close()


# webscrape_util.create_database("auchan")
# webscrape_util.create_database("tesco")
# webscrape_util.create_database("aldi")

get_all_price_tesco()
mysql_conn.close()
















