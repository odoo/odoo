#
# test cases for related fields, etc.
#

from openerp.osv import fields
from openerp.tests import common


class TestRelatedField(common.TransactionCase):

    def setUp(self):
        super(TestRelatedField, self).setUp()
        self.partner = self.registry('res.partner')
        self.company = self.registry('res.company')

    def test_0_related(self):
        """ test an usual related field """
        # find a company with a non-null partner_id
        ids = self.company.search(self.cr, self.uid, [('partner_id', '!=', False)], limit=1)
        id = ids[0]

        # find partners that satisfy [('partner_id.company_id', '=', id)]
        company_ids = self.company.search(self.cr, self.uid, [('partner_id', '=', id)])
        partner_ids1 = self.partner.search(self.cr, self.uid, [('company_id', 'in', company_ids)])
        partner_ids2 = self.partner.search(self.cr, self.uid, [('related_company_partner_id', '=', id)])
        self.assertEqual(partner_ids1, partner_ids2)

    def do_test_company_field(self, field):
        # get a partner with a non-null company_id
        ids = self.partner.search(self.cr, self.uid, [('company_id', '!=', False)], limit=1)
        partner = self.partner.browse(self.cr, self.uid, ids[0])

        # check reading related field
        self.assertEqual(partner[field], partner.company_id)

        # check that search on related field is equivalent to original field
        ids1 = self.partner.search(self.cr, self.uid, [('company_id', '=', partner.company_id.id)])
        ids2 = self.partner.search(self.cr, self.uid, [(field, '=', partner.company_id.id)])
        self.assertEqual(ids1, ids2)

    def test_1_single_related(self):
        """ test a related field with a single indirection like fields.related('foo') """
        self.do_test_company_field('single_related_company_id')

    def test_2_related_related(self):
        """ test a related field referring to a related field """
        self.do_test_company_field('related_related_company_id')

    def test_3_read_write(self):
        """ write on a related field """
        # find a company with a non-null partner_id
        company_ids = self.company.search(self.cr, self.uid, [('partner_id', '!=', False)], limit=1)
        company = self.company.browse(self.cr, self.uid, company_ids[0])

        # find partners that satisfy [('partner_id.company_id', '=', company.id)]
        partner_ids = self.partner.search(self.cr, self.uid, [('related_company_partner_id', '=', company.id)])
        partner = self.partner.browse(self.cr, self.uid, partner_ids[0])

        # create a new partner, and assign it to company
        new_partner_id = self.partner.create(self.cr, self.uid, {'name': 'Foo'})
        partner.write({'related_company_partner_id': new_partner_id})

        company = self.company.browse(self.cr, self.uid, company_ids[0])
        self.assertEqual(company.partner_id.id, new_partner_id)

        partner = self.partner.browse(self.cr, self.uid, partner_ids[0])
        self.assertEqual(partner.related_company_partner_id.id, new_partner_id)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
