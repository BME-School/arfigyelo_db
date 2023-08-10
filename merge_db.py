import sqlite3
import mysql.connector


def create_tables(dbs, cursor):
    # Új tábla létrehozása a termékeknek és az áraknak a merged_db-ben
    columns = ['name', 'category']
    columns.extend(dbs)
    cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY,
                {", ".join(f"{col} TEXT" for col in columns)},
                {", ".join(f"{col}_price INTEGER" for col in columns[2:])},
                best_price INTEGER
            )
        ''')
    print("adatbázis sikeresen létrehozva.")


def delete_rows(dbs, cursor):
    sql = "DELETE FROM products WHERE NOT ("
    for i in range(len(dbs)):
        for j in range(i+1, len(dbs)):
            sql += f" {dbs[i]} IS NOT NULL AND {dbs[j]} IS NOT NULL OR"

    sql = sql[:-3] + ")"
    cursor.execute(sql)
    print("Hiányos sorok sikeresen törölve.")


def add_databases(dbs, cursor):
    for db in dbs:
        db_conn = sqlite3.connect(f'databases/adatbazis_{db}.db')
        db_cursor = db_conn.cursor()

        # Összekapcsolás a merged_db products táblával a név alapján
        db_cursor.execute('SELECT sku, name, category FROM products')
        products = db_cursor.fetchall()
        for sku, name, category in products:
            cursor.execute('''
                        SELECT id FROM products
                        WHERE name = ?
                    ''', (name, ))
            existing_product = cursor.fetchone()

            if existing_product:
                # Ha már van azonos név és kategória a merged_db-ben, akkor frissítjük az sku-t
                cursor.execute(f'''
                            UPDATE products
                            SET {db} = ?
                            WHERE id = ?
                        ''', (sku, existing_product[0]))
            else:
                cursor.execute(f'''
                            INSERT INTO products (name, category, {db})
                            VALUES (?, ?, ?)
                        ''', (name, category, sku))
        db_conn.close()
        print(f"adatbázis -{db}- termékei és árai sikeresen hozzáadva")


def update_price(dbs, cursor):
    for db in dbs:
        db_conn = sqlite3.connect(f'databases/adatbazis_{db}.db')
        db_cursor = db_conn.cursor()

        cursor.execute(f'SELECT {db}, name, category FROM products')
        products = cursor.fetchall()
        for sku, name, category in products:
            db_cursor.execute(f'''SELECT discount_price FROM prices 
                                            WHERE product_sku = ?
                                            ORDER BY discount_price ASC LIMIT 1;''', (sku,))
            lowest_price = db_cursor.fetchone()
            db_cursor.execute(f'''SELECT discount_price FROM prices 
                                            WHERE product_sku = ?
                                            ORDER BY date DESC LIMIT 1;''', (sku,))
            actual_price = db_cursor.fetchone()

            try:
                cursor.execute(f'''UPDATE products
                            SET best_price = CASE
                                                WHEN (best_price IS NULL OR {lowest_price[0]} < best_price) THEN {lowest_price[0]}
                                                ELSE best_price
                                                END,
                                {db}_price = ?
                            WHERE name = ?
                            ''', (actual_price[0], name))
            except TypeError:
                pass
        print(f"{db} árak frissítveí")


def db_merge():
    # Az adatbázisok neveit a tömbben kell megadni
    databases = ["tesco", "auchan"]

    # Adatbáziskapcsolat létrehozása
    merged_conn = sqlite3.connect('databases/merged_db.db')
    merged_cursor = merged_conn.cursor()

    # Új tábla létrehozása a termékeknek és az áraknak a merged_db-ben
    create_tables(databases, merged_cursor,)
    merged_conn.commit()

    # Adatbázisok összekapcsolása
    add_databases(databases, merged_cursor)
    merged_conn.commit()

    # Töröljük azokat a sorokat ahol nincs meg legalább 2 üzlet ára
    delete_rows(databases, merged_cursor)
    merged_conn.commit()

    # Frissítsük az árakat
    update_price(databases, merged_cursor)
    merged_conn.commit()

    # Adatbázis lezárása
    merged_conn.close()


# db_merge()

db_config = {
    "host": "localhost",
    "user": "admin",
    "password": "admin",
    "database": "arfigyelo"
}

mysql_conn = mysql.connector.connect(**db_config)
mysql_cursor = mysql_conn.cursor()


def update_mysql_row(sku, img):
    mysql_cursor.execute(f"SELECT * FROM products WHERE tesco=%s", (sku,))
    result = mysql_cursor.fetchone()
    if result:
        mysql_cursor.execute(f"UPDATE products SET img = %s WHERE tesco=%s", (img, sku))
        mysql_conn.commit()


def add_product_image():
    db_conn = sqlite3.connect(f'databases/tesco_img_link.db')
    db_cursor = db_conn.cursor()
    db_cursor.execute('SELECT * FROM products')
    products = db_cursor.fetchall()
    for p in products:
        update_mysql_row(p[0], p[3])


# add_product_image()
mysql_conn.close()


