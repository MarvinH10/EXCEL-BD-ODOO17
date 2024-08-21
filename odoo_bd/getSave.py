import xmlrpc.client
import mysql.connector
import contextlib

""" CONEXIÓN A ODOO VERSION 17 """
ODOO_URL = "https://kdoshstoreproof.odoo.com"
ODOO_BD = "kdoshstoreproof"
ODOO_USERNAME = "j99crispin@gmail.com"
ODOO_PASSWORD = "952fe0212b885854888fb8f720ce64d448512e30"

""" ACA CONECTAREMOS A ODOO """
def get_odoo_connection():
    common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
    uid = common.authenticate(ODOO_BD, ODOO_USERNAME, ODOO_PASSWORD, {})
    if not uid:
        print("Error en la autenticación!")
        return None, None
    models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")
    return uid, models

""" OBTENDREMOS LOS PRODUCTOS Y SUS VARIANTES """
def conect_get_product(uid, models):
    domain = [['type', '=', 'product']]
    fields = ["id", "name", "default_code", "categ_id", "type"]
    productos = models.execute_kw(ODOO_BD, uid, ODOO_PASSWORD, 'product.template', 'search_read', [domain], {'fields': fields})

    variant_fields = ["id", "name", "default_code", "product_tmpl_id", "categ_id"]
    variantes = models.execute_kw(ODOO_BD, uid, ODOO_PASSWORD, 'product.product', 'search_read', [domain], {'fields': variant_fields})

    attribute_lines = models.execute_kw(
        ODOO_BD, uid, ODOO_PASSWORD, 'product.template.attribute.value', 'search_read',
        [[['product_tmpl_id', 'in', [p['id'] for p in productos]]]], {'fields': ['product_tmpl_id', 'attribute_id', 'product_attribute_value_id']}
    )
    attribute_values_dict = {}
    for line in attribute_lines:
        product_id = line['product_tmpl_id'][0]
        attribute_value = models.execute_kw(
            ODOO_BD, uid, ODOO_PASSWORD, 'product.attribute.value', 'read', [line['product_attribute_value_id'][0]], {'fields': ['name']}
        )
        if product_id not in attribute_values_dict:
            attribute_values_dict[product_id] = []
        attribute_values_dict[product_id].append(attribute_value[0]['name'])

    return productos, variantes, attribute_values_dict

    print(f"Error al obtener los productos: {e}")

""" OBTENDREMOS LOS PROVEEDORES """
def conect_get_proveedores(uid, models):
    domain = []
    fields = ["id", "name"]
    proveedores = models.execute_kw(ODOO_BD, uid, ODOO_PASSWORD, 'res.partner', 'search_read', [domain], {'fields': fields})

    return proveedores

    print(f"Error al obtener los productos: {e}")

""" GENERADOR PARA INSERCIÓN A LA BASE DE DATOS """
@contextlib.contextmanager
def mysql_connection():
    conn = mysql.connector.connect(
        host='localhost',
        database='odoo_bd',
        user='root',
        password='210701'
    )
    try:
        yield conn
    finally:
        conn.close()

""" ACA GUARDAREMOS LA EXTRACCION DE LOS DATOS AL MYSQL DE LOS PRODUCTOS """
def save_product_mysql(productos, variantes, attribute_values_dict):
    with mysql_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("DELETE FROM productos")
        cursor.execute("DELETE FROM variantes")
        cursor.execute("ALTER TABLE productos AUTO_INCREMENT = 1")
        cursor.execute("ALTER TABLE variantes AUTO_INCREMENT = 1")

        for producto in productos:
            prod_id = producto.get('id', '')
            nombre = producto.get('name', '')
            referencia_interna = producto.get('default_code', '')
            categoria = producto.get('categ_id')[1] if producto.get('categ_id') else ''

            atributos = ', '.join(attribute_values_dict.get(prod_id, []))

            insert_query = """ 
             INSERT INTO productos (prod_id, nombre, referencia_interna, categoria, atributos)
             VALUES (%s, %s, %s, %s, %s)
             """
            cursor.execute(insert_query, (prod_id, nombre, referencia_interna, categoria, atributos))

        for variante in variantes:
            variant_id = variante.get('id', '')
            nombre_variante = variante.get('name', '')
            referencia_interna_variante = variante.get('default_code', '')
            producto_id = variante.get('product_tmpl_id')[0] if variante.get('product_tmpl_id') else None
            categoria_variante = variante.get('categ_id')[1] if variante.get('categ_id') else ''

            insert_variant_query = """ 
             INSERT INTO variantes (variant_id, nombre, referencia_interna, categoria, producto_id)
             VALUES (%s, %s, %s, %s, %s)
             """
            cursor.execute(insert_variant_query, (variant_id, nombre_variante, referencia_interna_variante, categoria_variante, producto_id))

        conn.commit()
        print("Se almaceno correctamente a la BD los productos/variantes.")

""" ACA GUARDAREMOS LA EXTRACCION DE LOS DATOS AL MYSQL DE LOS PROVEEDORES """
def save_proveedores_mysql(proveedores):
    with mysql_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("DELETE FROM proveedores")
        cursor.execute("ALTER TABLE proveedores AUTO_INCREMENT = 1")

        for proveedor in proveedores:
            proveedor_nombre = proveedor.get('name', '')

            insert_supplier_query = """
             INSERT INTO proveedores (proveedor_nombre)
             VALUES (%s)
             """
            cursor.execute(insert_supplier_query, (proveedor_nombre,))

        conn.commit()
        print("Se almaceno correctamente a la BD los proveedores.")

""" FUNCION FINAL Y PRINCIPAL PARA EJECUTAR EL PROCESO COMPLETO """
def main():
    uid, models = get_odoo_connection()
    if not uid:
        return

    productos, variantes, attribute_values_dict = conect_get_product(uid, models)
    proveedores = conect_get_proveedores(uid, models)

    if productos or variantes:
        save_product_mysql(productos, variantes, attribute_values_dict)
    if proveedores:
        save_proveedores_mysql(proveedores)
    else:
        print("Error al almacenar los datos almacenado de Odoo versión 17.")

if __name__ == "__main__":
    main()
