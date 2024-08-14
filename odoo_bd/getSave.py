import xmlrpc.client
import mysql.connector
from mysql.connector import Error

""" ACA CONECTAREMOS A ODOO Y OBTENDREMOS LOS PRODUCTOS Y SUS VARIANTES """
def conect_get_product():
    try:
        URL = "https://kdoshstoreproof.odoo.com"
        DB = "kdoshstoreproof"
        USERNAME = "j99crispin@gmail.com"
        PASSWORD = "952fe0212b885854888fb8f720ce64d448512e30"

        common = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/common")
        uid = common.authenticate(DB, USERNAME, PASSWORD, {})
        if not uid:
            print("Error en la autenticación!")
            return [], [], {}, []

        models = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/object")
        domain = [['type', '=', 'product']]
        fields = ["id", "name", "default_code", "categ_id", "type"]
        productos = models.execute_kw(DB, uid, PASSWORD, 'product.template', 'search_read', [domain], {'fields': fields})
        print(f"Se encontraron {len(productos)} productos.")

        variant_fields = ["id", "name", "default_code", "product_tmpl_id", "categ_id"]
        variantes = models.execute_kw(DB, uid, PASSWORD, 'product.product', 'search_read', [domain], {'fields': variant_fields})
        print(f"Se encontraron {len(variantes)} variantes.")

        attribute_lines = models.execute_kw(
            DB, uid, PASSWORD, 'product.template.attribute.value', 'search_read',
            [[['product_tmpl_id', 'in', [p['id'] for p in productos]]]], {'fields': ['product_tmpl_id', 'attribute_id', 'product_attribute_value_id']}
        )
        attribute_values_dict = {}
        for line in attribute_lines:
            product_id = line['product_tmpl_id'][0]
            attribute_value = models.execute_kw(
                DB, uid, PASSWORD, 'product.attribute.value', 'read', [line['product_attribute_value_id'][0]], {'fields': ['name']}
            )
            if product_id not in attribute_values_dict:
                attribute_values_dict[product_id] = []
            attribute_values_dict[product_id].append(attribute_value[0]['name'])

        return productos, variantes, attribute_values_dict

    except Exception as e:
        print(f"Error al obtener los productos: {e}")
        return [], [], {}

""" ACA CONECTAREMOS A ODOO Y OBTENDREMOS LOS PROVEEDORES """
def conect_get_proveedores():
    try:
        URL = "https://kdoshstoreproof.odoo.com"
        DB = "kdoshstoreproof"
        USERNAME = "j99crispin@gmail.com"
        PASSWORD = "952fe0212b885854888fb8f720ce64d448512e30"

        common = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/common")
        uid = common.authenticate(DB, USERNAME, PASSWORD, {})
        if not uid:
            print("Error en la autenticación!")
            return []

        models = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/object")
        domain = []
        fields = ["id", "name"]
        proveedores = models.execute_kw(DB, uid, PASSWORD, 'res.partner', 'search_read', [domain], {'fields': fields})
        print(f"Se encontraron {len(proveedores)} proveedores.")

        return proveedores

    except Exception as e:
        print(f"Error al obtener los productos: {e}")
        return []

""" ACA GUARDAREMOS LA EXTRACCION DE LOS DATOS AL MYSQL DE LOS PRODUCTOS """
def save_product_mysql(productos, variantes, attribute_values_dict):
    try:
        conexion = mysql.connector.connect(
            host='localhost',
            database='odoo_bd',
            user='root',
            password=''
        )

        if conexion.is_connected():
            print("Conexión exitosa con la base de datos MySQL.")
            cursor = conexion.cursor()

            delete_query = "DELETE FROM productos"
            cursor.execute(delete_query)
            delete_variant_query = "DELETE FROM variantes"
            cursor.execute(delete_variant_query)
            print("Todos los registros existentes han sido borrados.")

            reset_auto_increment_query = "ALTER TABLE productos AUTO_INCREMENT = 1"
            cursor.execute(reset_auto_increment_query)
            reset_variant_auto_increment_query = "ALTER TABLE variantes AUTO_INCREMENT = 1"
            cursor.execute(reset_variant_auto_increment_query)

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

            conexion.commit()
            print("Datos insertados correctamente en la base de datos.")

    except Error as e:
        print(f"Error al insertar los productos: {e}")

    finally:
        if conexion.is_connected():
            cursor.close()
            conexion.close()
            print("Conexión cerrada.")

""" ACA GUARDAREMOS LA EXTRACCION DE LOS DATOS AL MYSQL DE LOS PROVEEDORES """
def save_proveedores_mysql(proveedores):
    try:
        conexion = mysql.connector.connect(
            host='localhost',
            database='odoo_bd',
            user='root',
            password=''
        )
        if conexion.is_connected():
            print("Conexión exitosa con la base de datos MySQL para proveedores.")
            cursor = conexion.cursor()

            cursor.execute("DELETE FROM proveedores")

            for proveedor in proveedores:
                proveedor_nombre = proveedor.get('name', '')

                insert_supplier_query = """
                 INSERT INTO proveedores (proveedor_nombre)
                 VALUES (%s)
                 """
                cursor.execute(insert_supplier_query, (proveedor_nombre,))

            conexion.commit()
            print("Datos de proveedores insertados correctamente en la base de datos.")

    except Error as e:
        print(f"Error al insertar los proveedores: {e}")

    finally:
        if conexion.is_connected():
            cursor.close()
            conexion.close()
            print("Conexión cerrada para proveedores.")

""" FUNCION FINAL Y PRINCIPAL PARA EJECUTAR EL PROCESO COMPLETO """
def main():
    productos, variantes, attribute_values_dict = conect_get_product()
    proveedores = conect_get_proveedores()

    if productos or variantes:
        save_product_mysql(productos, variantes, attribute_values_dict)
    if proveedores:
        save_proveedores_mysql(proveedores)

if __name__ == "__main__":
    main()
