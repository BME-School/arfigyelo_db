from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re
import time
import webscrape_util
import sqlite3


# Chrome options
options = Options()
# options.add_argument("--headless") # Böngészőt ne nyissa meg
# options.add_experimental_option("prefs", {"profile.managed_default_content_settings.images": 2})  # Ne töltse meg a képeket
# options.add_argument("--disable-dev-shm-usage")


def create_merged_database():
    conn = sqlite3.connect(f'databases/merged.db')
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id TEXT PRIMARY KEY,
            name TEXT,
            category TEXT,
            img TEXT,
            best_price INT,
            tesco TEXT,
            tesco_price INT,
            auchan TEXT,
            auchan_price INT,
            spar TEXT,
            spar_price INT,
            aldi TEXT,
            aldi_price INT,
            penny TEXT,
            penny_price INT
        )
    ''')

    conn.commit()
    conn.close()

create_merged_database()
# Összevont adatbázis
merged_conn = sqlite3.connect('databases/merged.db')
merged_cursor = merged_conn.cursor()

# Visszaadja az első "xxx Ft" formátumú szövegből az árat egész számként
def get_first_price(txt):
    match = re.search(r'\b([\d\s.,]+) Ft\b', txt)
    return int(float(match.group(1).replace(",", "").replace(" ", ""))) if match else 0


# tesco
def get_all_price_tesco():
    def gorgetes():
        current_position = driver.execute_script("return window.pageYOffset;")
        new_position = current_position + 440
        driver.execute_script(f"window.scrollTo(0, {new_position});")
        time.sleep(0.2)
    category = webscrape_util.get_category_tesco()
    conn = sqlite3.connect('databases/adatbazis_tesco.db')
    c = conn.cursor()
    for cg in category:
        i = 1
        category_name = cg.split("/")[6]
        while True:
            driver = webdriver.Chrome(options=options)
            driver.get(cg+f"&page={i}&count=48")
            i += 1

            products = driver.find_elements(By.CLASS_NAME, "product-list--list-item")
            for _ in range(12):
                gorgetes()
            if len(products) == 0:
                break
            products_sql = []
            prices_sql = []
            merged1 = []
            merged2 = []
            for j in products:
                p = j.find_element(By.CLASS_NAME, "product-details--wrapper")
                element = p.find_element(By.CSS_SELECTOR, "h3 a")
                sku = element.get_attribute("href").split("/")[-1]
                name = p.find_element(By.CSS_SELECTOR, "h3 span").get_attribute("innerHTML")
                image = j.find_element(By.CSS_SELECTOR, ".product-image").get_attribute("src")
                products_sql.append((sku, category_name, name, sku))
                try:
                    price = get_first_price(p.find_element(By.CLASS_NAME, "beans-price__text").text)
                    discount = p.find_elements(By.CLASS_NAME, "offer-text")
                except NoSuchElementException:
                    continue
                clubcard_price = get_first_price(discount[0].text) if len(discount) > 0 else price
                clubcard_price = price if clubcard_price == 0 else clubcard_price

                prices_sql.append((price, clubcard_price, sku))
                merged1.append((name, category_name, image, name))
                merged2.append((clubcard_price, sku, name))

            insert_products = "INSERT INTO products (sku, category, name) SELECT ?, ?, ? WHERE NOT EXISTS (SELECT 1 FROM products WHERE sku = ?)"
            insert_prices = "INSERT INTO prices (normal_price, discount_price, product_sku) VALUES (?, ?, ?)"
            c.executemany(insert_products, products_sql)
            c.executemany(insert_prices, prices_sql)
            conn.commit()

            merged_insert_products = "INSERT INTO products (name, category, img) SELECT ?, ?, ? WHERE NOT EXISTS (SELECT 1 FROM products WHERE name = ?)"
            merged_update = "UPDATE products SET tesco_price = ?, tesco = ?, best_price = CASE WHEN tesco_price > best_price THEN tesco_price ELSE best_price END WHERE name = ?"
            merged_cursor.executemany(merged_insert_products, merged1)
            merged_cursor.executemany(merged_update, merged2)
            merged_conn.commit()

            conn.commit()
            driver.quit()
    conn.close()


# aldi
def get_all_price_aldi():
    category = webscrape_util.get_category_aldi()
    conn = sqlite3.connect('databases/adatbazis_aldi.db')
    c = conn.cursor()
    driver = webdriver.Chrome(options=options)

    for cg in category:
        driver.get(cg)
        try:
            category_name = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, "h1"))).text
        except TimeoutException:
            print(cg)
            category.append(cg)
            continue

        products_sql = []
        prices_sql = []
        merged1 = []
        merged2 = []
        while True:
            original_url = driver.current_url
            driver.execute_script(f"window.scrollTo(0, {driver.execute_script('return window.pageYOffset;') + 600});")
            time.sleep(1)
            driver.execute_script(f"window.scrollTo(0, {driver.execute_script('return window.pageYOffset;') + 600});")
            time.sleep(0.5)
            driver.find_element(By.TAG_NAME, "body").send_keys(Keys.END)
            if driver.current_url == original_url:
                time.sleep(1)
                driver.find_element(By.TAG_NAME, "body").send_keys(Keys.END)
                time.sleep(1)
                if driver.current_url == original_url:
                    break

        products = driver.find_elements(By.CLASS_NAME, "product-card-cotainer-w")
        for p in products:
            element = p.find_element(By.CLASS_NAME, "product-card-text").find_element(By.CLASS_NAME, "product-card-image-link")
            name = element.find_element(By.CSS_SELECTOR, "span").get_attribute("innerHTML")
            sku = element.get_attribute("href").split("/")[-1]
            image = p.find_element(By.CSS_SELECTOR, ".product-card-image-link img").get_attribute("src")
            print(image)
            products_sql.append((sku, category_name, name, sku))

            price = p.find_element(By.CSS_SELECTOR, 'span[itemprop="price"]').text
            price = ''.join(filter(str.isdigit, price))
            try:
                old_price = p.find_element(By.CLASS_NAME, "old-price-container").find_element(By.CSS_SELECTOR, "span")
                try:
                    old_price = get_first_price(old_price.text.replace("\u202f", ""))
                except ValueError:
                    print(old_price.text)
                discount_price = price if old_price == 0 else old_price
            except NoSuchElementException:
                discount_price = price
            prices_sql.append((price, discount_price, sku))
            merged1.append((name, category_name, image, name))
            merged2.append((sku, discount_price, name))

        insert_products = "INSERT INTO products (sku, category, name) SELECT ?, ?, ? WHERE NOT EXISTS (SELECT 1 FROM products WHERE sku = ?)"
        insert_prices = "INSERT INTO prices (normal_price, discount_price, product_sku) VALUES (?, ?, ?)"
        c.executemany(insert_products, products_sql)
        c.executemany(insert_prices, prices_sql)
        conn.commit()

        merged_insert_products = "INSERT INTO products (name, category, img) SELECT ?, ?, ? WHERE NOT EXISTS (SELECT 1 FROM products WHERE name = ?)"
        merged_update = "UPDATE products SET aldi = ?, aldi_price = ?, best_price = CASE WHEN aldi_price > best_price THEN aldi_price ELSE best_price END WHERE name = ?"
        merged_cursor.executemany(merged_insert_products, merged1)
        merged_cursor.executemany(merged_update, merged2)
        merged_conn.commit()

    driver.quit()
    conn.close()

# auchan
def get_all_price_auchan():
    def gorgetes():
        current_position = driver.execute_script("return window.pageYOffset;")
        new_position = current_position + 440
        driver.execute_script(f"window.scrollTo(0, {new_position});")
        time.sleep(2)
    category = webscrape_util.get_category_auchan()
    conn = sqlite3.connect('databases/adatbazis_auchan.db')
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
        merged1 = []
        merged2 = []
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
                image = products[i * 5 + j].find_element(By.CSS_SELECTOR, "._1P6B69Si picture source").get_attribute("data-srcset")
                print(image)

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
                merged1.append((name, category_name, image, name))
                merged2.append((sku, discount_price, name))
            gorgetes()

        insert_products = "INSERT INTO products (sku, category, name) SELECT ?, ?, ? WHERE NOT EXISTS (SELECT 1 FROM products WHERE sku = ?)"
        insert_prices = "INSERT INTO prices (normal_price, discount_price, product_sku) VALUES (?, ?, ?)"
        c.executemany(insert_products, products_sql)
        c.executemany(insert_prices, prices_sql)
        conn.commit()

        merged_insert_products = "INSERT INTO products (name, category, img) SELECT ?, ?, ? WHERE NOT EXISTS (SELECT 1 FROM products WHERE name = ?)"
        merged_update = "UPDATE products SET auchan = ?, auchan_price = ?, best_price = CASE WHEN aldi_price > best_price THEN aldi_price ELSE best_price END WHERE name = ?"
        merged_cursor.executemany(merged_insert_products, merged1)
        merged_cursor.executemany(merged_update, merged2)
        merged_conn.commit()

    driver.quit()
    conn.close()


# penny
def get_all_price_penny():
    category = webscrape_util.get_category_penny()
    conn = sqlite3.connect('databases/adatbazis_penny.db')
    c = conn.cursor()
    driver = webdriver.Chrome(options=options)

    for cg in category:
        driver.get(cg)
        try:
            category_name = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, "h1"))).text
        except TimeoutException:
            print(cg)
            category.append(cg)
            continue

        while True:
            original_url = driver.current_url
            driver.execute_script(f"window.scrollTo(0, {driver.execute_script('return window.pageYOffset;') + 600});")
            time.sleep(1)
            driver.execute_script(f"window.scrollTo(0, {driver.execute_script('return window.pageYOffset;') + 600});")
            time.sleep(0.5)
            driver.find_element(By.TAG_NAME, "body").send_keys(Keys.END)
            if driver.current_url == original_url:
                time.sleep(1)
                driver.find_element(By.TAG_NAME, "body").send_keys(Keys.END)
                time.sleep(1)
                if driver.current_url == original_url:
                    break

        products_sql = []
        prices_sql = []
        merged1 = []
        merged2 = []

        products = driver.find_elements(By.CLASS_NAME, "product-card")
        for p in products:
            element = p.find_element(By.CLASS_NAME, "product-card-text").find_element(By.CLASS_NAME, "product-card-image-link")
            name = element.find_element(By.CSS_SELECTOR, "span").get_attribute("innerHTML")
            sku = element.get_attribute("href").split("/")[-1]
            image_div = p.find_element(By.CLASS_NAME, "product-card-img")
            image = image_div.find_element(By.CSS_SELECTOR, "img").get_attribute("src")

            price = p.find_element(By.CSS_SELECTOR, 'span[itemprop="price"]').text
            price = ''.join(filter(str.isdigit, price))
            try:
                old_price = p.find_element(By.CLASS_NAME, "old-price-container").find_element(By.CSS_SELECTOR, "span")
                try:
                    old_price = get_first_price(old_price.text.replace("\u202f", ""))
                except ValueError:
                    print(old_price.text)
                discount_price = price if old_price == 0 else old_price
            except NoSuchElementException:
                discount_price = price
            prices_sql.append((price, discount_price, sku))
            merged1.append((name, category_name, image, name))
            merged2.append((sku, discount_price, name))

        insert_products = "INSERT INTO products (sku, category, name) SELECT ?, ?, ? WHERE NOT EXISTS (SELECT 1 FROM products WHERE sku = ?)"
        insert_prices = "INSERT INTO prices (normal_price, discount_price, product_sku) VALUES (?, ?, ?)"
        c.executemany(insert_products, products_sql)
        c.executemany(insert_prices, prices_sql)
        conn.commit()

        merged_insert_products = "INSERT INTO products (name, category, img) SELECT ?, ?, ? WHERE NOT EXISTS (SELECT 1 FROM products WHERE name = ?)"
        merged_update = "UPDATE products SET penny = ?, penny_price = ?, best_price = CASE WHEN aldi_price > best_price THEN aldi_price ELSE best_price END WHERE name = ?"
        merged_cursor.executemany(merged_insert_products, merged1)
        merged_cursor.executemany(merged_update, merged2)
        merged_conn.commit()

    driver.quit()
    conn.close()

get_all_price_penny()