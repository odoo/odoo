# Elimina todos los contactos y cuentas (res.partner) excepto los protegidos
# Ejecutar con: ./odoo-bin shell -c debian/odoo.conf -d <db_name> --scripts scripts/delete_all_partners.py

try:
    confirm = input("¿Seguro que quieres eliminar TODOS los contactos/cuentas excepto el principal? (sí/no): ")
    if confirm.lower() != "sí":
        print("Operación cancelada.")
    else:
        main_partner = env.ref('base.main_partner')
        partners = env['res.partner'].search([('id', '!=', main_partner.id)])
        deleted_count = len(partners)
        partners.unlink()
        print(f"Eliminados {deleted_count} contactos/cuentas (res.partner)")
except Exception as e:
    print(f"Error: {e}")
