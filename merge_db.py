import sqlite3

def create_tables(merged_cursor, merged_conn, databases):
    # Új tábla létrehozása a termékeknek és az áraknak a merged_db-ben
    columns = ['name', 'category']
    columns.extend(databases)
    merged_cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY,
                {", ".join(f"{col} TEXT" for col in columns)}
            )
        ''')
    merged_cursor.execute('''
            CREATE TABLE IF NOT EXISTS prices (
                date INTEGER DEFAULT (strftime('%s', 'now')),
                normal_price INTEGER,
                discount_price INTEGER,
                product_sku TEXT,
                product_id INT,
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
        ''')
    merged_conn.commit()
    print("adatbázis létrehozva")


def db_merge():
    # Adatbáziskapcsolat létrehozása
    # Új adatbázis hozzáadásához csak bővíteni kell a databases tömböt
    databases = ["tesco", "auchan"]
    merged_conn = sqlite3.connect('databases/merged_db.db')
    merged_cursor = merged_conn.cursor()

    # Új tábla létrehozása a termékeknek és az áraknak a merged_db-ben
    create_tables(merged_cursor, merged_conn, databases)
    # Adatbázisok összekapcsolása
    for db in databases[0:0]:
        db_conn = sqlite3.connect(f'databases/adatbazis_{db}.db')
        db_cursor = db_conn.cursor()

        # Összekapcsolás a merged_db products táblával a név alapján
        db_cursor.execute('SELECT sku, name, category FROM products')
        products = db_cursor.fetchall()
        for sku, name, category in products:
            merged_cursor.execute('''
                        SELECT id FROM products
                        WHERE name = ?
                    ''', (name, ))
            existing_product = merged_cursor.fetchone()

            if existing_product:
                # Ha már van azonos név és kategória a merged_db-ben, akkor frissítjük az sku-t
                merged_cursor.execute(f'''
                            UPDATE products
                            SET {db} = ?
                            WHERE id = ?
                        ''', (sku, existing_product[0]))
            else:
                merged_cursor.execute(f'''
                            INSERT INTO products (name, category, {db})
                            VALUES (?, ?, ?)
                        ''', (name, category, sku))
        db_cursor.execute('SELECT date, normal_price, discount_price, product_sku FROM prices')
        prices = db_cursor.fetchall()
        for date, normal_price, discount_price, product_sku in prices:
            merged_cursor.execute('''
                                INSERT INTO prices (date, normal_price, discount_price, product_sku)
                                VALUES (?, ?, ?, ?)
                                ''', (date, normal_price, discount_price, product_sku))

        db_conn.close()
        merged_conn.commit()
        print(f"adatbázis -{db}- sikeresen hozzáadva")


    # Adatbázis lezárása
    merged_conn.close()

db_merge()
