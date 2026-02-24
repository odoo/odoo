# Elimina todos los contactos y cuentas (res.partner) excepto los protegidos
# Ejecutar con: ./odoo-bin shell -c debian/odoo.conf -d <db_name> --scripts scripts/delete_all_partners.py

# Obtiene el partner principal de la compañía (no se debe borrar)
main_partner = env.ref('base.main_partner')

# Busca todos los partners excepto el principal
partners = env['res.partner'].search([('id', '!=', main_partner.id)])

# Borra los partners encontrados
deleted_count = len(partners)
partners.unlink()

print(f"Eliminados {deleted_count} contactos/cuentas (res.partner)")
