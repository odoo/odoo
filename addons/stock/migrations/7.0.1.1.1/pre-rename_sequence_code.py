__name__ = ("update internal picking sequence code and sequence")

def migrate(cr, version):
    old_type = 'stock.picking'
    new_type = 'stock.picking.internal'
    cr.execute ("UPDATE ir_sequence_type SET code=%(newtype)s WHERE code=%(oldtype)s",
                {'newtype': new_type,
                 'oldtype': old_type})
    cr.execute ("UPDATE ir_sequence SET code=%(newtype)s WHERE code=%(oldtype)s",
                {'newtype': new_type,
                 'oldtype': old_type})
