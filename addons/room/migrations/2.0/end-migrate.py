from odoo.db.schema import table_exists

ROOM_TABLES = ("room_booking", "room_room", "room_office")


def migrate(cr, version):
    if not version:
        return
    for table in ROOM_TABLES:
        if table_exists(cr, table):
            cr.execute(f'DROP TABLE "{table}" CASCADE')
