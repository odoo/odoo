#
# test exception with m2m indexes on long model names
#
from openerp.tests import common
from openerp.exceptions import except_orm


class TestNewFields(common.TransactionCase):

    def test_m2m_raises(self):
        IrModel = self.env['ir.model']
        mname = 'x_test.model.with.a.ridiculously.long.name.can.you.believe.this'

        data = {'name': mname,
                'model': mname,
                'state': 'manual',
                'osv_memory': False,
                }
        model = IrModel.create(data)
        field = {
            'name': 'x_m2m',
            'model': mname,
            'relation': 'res.partner.category',
            'ttype': 'many2many',
            'state': 'manual',
            'model_id': model.id,
            }
        with self.assertRaises(ValueError) as cm:
            self.env['ir.model.fields'].create(field)
        self.assertTrue(str(cm.exception).startswith('Creation of m2m table'))
        self.env['ir.model.access'].create({'name': 'test',
                                            'model_id': model.id,
                                            })
        self.env.cr.commit() # suppress warning on missing ACL
