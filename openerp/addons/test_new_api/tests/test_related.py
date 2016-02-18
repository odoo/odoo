#
# test cases for related fields, etc.
#
import unittest

from openerp.osv import fields
from openerp.tests import common

class TestRelatedField(common.TransactionCase):

    def setUp(self):
        super(TestRelatedField, self).setUp()
        self.alpha = self.registry('test_new_api.alpha')
        self.bravo = self.registry('test_new_api.bravo')
        self.alpha_id = self.alpha.create(self.cr, self.uid, {'name': 'Alpha'})
        self.alpha.create(self.cr, self.uid, {'name': 'Beta'})
        self.bravo.create(self.cr, self.uid, {'alpha_id': self.alpha_id})

    def test_0_related(self):
        """ test an usual related field """
        # find bravos that satisfy [('alpha_id.name', '=', 'Alpha')]
        alpha_ids = self.alpha.search(self.cr, self.uid, [('name', '=', 'Alpha')])
        bravo_ids1 = self.bravo.search(self.cr, self.uid, [('alpha_id', 'in', alpha_ids)])
        bravo_ids2 = self.bravo.search(self.cr, self.uid, [('alpha_name', '=', 'Alpha')])
        self.assertEqual(bravo_ids1, bravo_ids2)

    def do_test_company_field(self, field):
        # get a bravo with a non-null alpha_id
        ids = self.bravo.search(self.cr, self.uid, [('alpha_id', '!=', False)])
        bravo = self.bravo.browse(self.cr, self.uid, ids[0])

        # check reading related field
        self.assertEqual(bravo[field], bravo.alpha_id)

        # check that search on related field is equivalent to original field
        ids1 = self.bravo.search(self.cr, self.uid, [('alpha_id', '=', bravo.alpha_id.id)])
        ids2 = self.bravo.search(self.cr, self.uid, [(field, '=', bravo.alpha_id.id)])
        self.assertEqual(ids1, ids2)

    def test_1_single_related(self):
        """ test a related field with a single indirection like fields.related('foo') """
        self.do_test_company_field('related_alpha_id')

    def test_2_double_related(self):
        """ test a related field referring to a related field """
        self.do_test_company_field('related_related_alpha_id')

    def test_3_read_write(self):
        """ write on a related field """
        # find an alpha with a non-null name
        alpha = self.alpha.browse(self.cr, self.uid, self.alpha_id)
        self.assertTrue(alpha.name)

        # find partners that satisfy [('alpha_id.name', '=', alpha.name)]
        bravo_ids = self.bravo.search(self.cr, self.uid, [('alpha_name', '=', alpha.name)])
        self.assertTrue(bravo_ids)
        bravo = self.bravo.browse(self.cr, self.uid, bravo_ids[0])

        # change the name of alpha through the related field, and check result
        NAME = 'Monthy Pythons'
        bravo.write({'alpha_name': NAME})
        self.assertEqual(bravo.alpha_id.name, NAME)
        self.assertEqual(bravo.alpha_name, NAME)


class TestPropertyField(common.TransactionCase):

    def setUp(self):
        super(TestPropertyField, self).setUp()
        self.user = self.registry('res.users')
        self.partner = self.registry('res.partner')
        self.company = self.registry('res.company')
        self.country = self.registry('res.country')
        self.property = self.registry('ir.property')
        self.imd = self.registry('ir.model.data')

    @unittest.skip("invalid monkey-patching")
    def test_1_property_multicompany(self):
        cr, uid = self.cr, self.uid

        parent_company_id = self.imd.get_object_reference(cr, uid, 'base', 'main_company')[1]
        country_be = self.imd.get_object_reference(cr, uid, 'base', 'be')[1]
        country_fr = self.imd.get_object_reference(cr, uid, 'base', 'fr')[1]
        group_partner_manager = self.imd.get_object_reference(cr, uid, 'base', 'group_partner_manager')[1]
        group_multi_company = self.imd.get_object_reference(cr, uid, 'base', 'group_multi_company')[1]

        sub_company = self.company.create(cr, uid, {'name': 'MegaCorp', 'parent_id': parent_company_id})
        alice = self.user.create(cr, uid, {'name': 'Alice',
            'login':'alice',
            'email':'alice@youcompany.com',
            'company_id':parent_company_id,
            'company_ids':[(6, 0, [parent_company_id, sub_company])],
            'country_id':country_be,
            'groups_id': [(6, 0, [group_partner_manager, group_multi_company])]
        })
        bob = self.user.create(cr, uid, {'name': 'Bob',
            'login':'bob',
            'email':'bob@megacorp.com',
            'company_id':sub_company,
            'company_ids':[(6, 0, [parent_company_id, sub_company])],
            'country_id':country_fr,
            'groups_id': [(6, 0, [group_partner_manager, group_multi_company])]
        })
        
        self.partner._columns = dict(self.partner._columns)
        self.partner._columns.update({
            'property_country': fields.property(type='many2one', relation="res.country", string="Country by company"),
        })
        self.partner._field_create(cr)

        partner_id = self.partner.create(cr, alice, {
            'name': 'An International Partner',
            'email': 'partner@example.com',
            'company_id': parent_company_id,
        })
        self.partner.write(cr, bob, [partner_id], {'property_country': country_fr})
        self.assertEqual(self.partner.browse(cr, bob, partner_id).property_country.id, country_fr, "Bob does not see the value he has set on the property field")

        self.partner.write(cr, alice, [partner_id], {'property_country': country_be})
        self.assertEqual(self.partner.browse(cr, alice, partner_id).property_country.id, country_be, "Alice does not see the value he has set on the property field")
        self.assertEqual(self.partner.browse(cr, bob, partner_id).property_country.id, country_fr, "Changes made by Alice have overwritten Bob's value")


class TestHtmlField(common.TransactionCase):

    def setUp(self):
        super(TestHtmlField, self).setUp()
        self.partner = self.registry('res.partner')

    def test_00_sanitize(self):
        cr, uid, context = self.cr, self.uid, {}
        old_columns = self.partner._columns
        self.partner._columns = dict(old_columns)
        self.partner._columns.update({
            'comment': fields.html('Secure Html', sanitize=False),
        })
        some_ugly_html = """<p>Oops this should maybe be sanitized
% if object.some_field and not object.oriented:
<table>
    % if object.other_field:
    <tr style="border: 10px solid black;">
        ${object.mako_thing}
        <td>
    </tr>
    % endif
    <tr>
%if object.dummy_field:
        <p>Youpie</p>
%endif"""

        pid = self.partner.create(cr, uid, {
            'name': 'Raoul Poilvache',
            'comment': some_ugly_html,
        }, context=context)
        partner = self.partner.browse(cr, uid, pid, context=context)
        self.assertEqual(partner.comment, some_ugly_html, 'Error in HTML field: content was sanitized but field has sanitize=False')

        self.partner._columns.update({
            'comment': fields.html('Unsecure Html', sanitize=True),
        })
        self.partner.write(cr, uid, [pid], {
            'comment': some_ugly_html,
        }, context=context)
        partner = self.partner.browse(cr, uid, pid, context=context)
        # sanitize should have closed tags left open in the original html
        self.assertIn('</table>', partner.comment, 'Error in HTML field: content does not seem to have been sanitized despise sanitize=True')
        self.assertIn('</td>', partner.comment, 'Error in HTML field: content does not seem to have been sanitized despise sanitize=True')
        self.assertIn('<tr style="', partner.comment, 'Style attr should not have been stripped')

        self.partner._columns['comment'] = fields.html('Stripped Html', sanitize=True, strip_style=True)
        self.partner.write(cr, uid, [pid], {'comment': some_ugly_html}, context=context)
        partner = self.partner.browse(cr, uid, pid, context=context)
        self.assertNotIn('<tr style="', partner.comment, 'Style attr should have been stripped')

        self.partner._columns = old_columns
