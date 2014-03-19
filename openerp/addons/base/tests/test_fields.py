#
# test cases for fields access, etc.
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
        # add a related field test_related_company_id on res.partner
        old_columns = self.partner._columns
        self.partner._columns = dict(old_columns)
        self.partner._columns.update({
            'related_company_partner_id': fields.related('company_id', 'partner_id', type='many2one', obj='res.partner'),
        })

        # find a company with a non-null partner_id
        ids = self.company.search(self.cr, self.uid, [('partner_id', '!=', False)], limit=1)
        id = ids[0]

        # find partners that satisfy [('partner_id.company_id', '=', id)]
        company_ids = self.company.search(self.cr, self.uid, [('partner_id', '=', id)])
        partner_ids1 = self.partner.search(self.cr, self.uid, [('company_id', 'in', company_ids)])
        partner_ids2 = self.partner.search(self.cr, self.uid, [('related_company_partner_id', '=', id)])
        self.assertEqual(partner_ids1, partner_ids2)

        # restore res.partner fields
        self.partner._columns = old_columns

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
        # add a related field test_related_company_id on res.partner
        # and simulate a _inherits_reload() to populate _all_columns.
        old_columns = self.partner._columns
        old_all_columns = self.partner._all_columns
        self.partner._columns = dict(old_columns)
        self.partner._all_columns = dict(old_all_columns)
        self.partner._columns.update({
            'single_related_company_id': fields.related('company_id', type='many2one', obj='res.company'),
        })
        self.partner._all_columns.update({
            'single_related_company_id': fields.column_info('single_related_company_id', self.partner._columns['single_related_company_id'], None, None, None)
        })

        self.do_test_company_field('single_related_company_id')

        # restore res.partner fields
        self.partner._columns = old_columns
        self.partner._all_columns = old_all_columns

    def test_2_related_related(self):
        """ test a related field referring to a related field """
        # add a related field on a related field on res.partner
        # and simulate a _inherits_reload() to populate _all_columns.
        old_columns = self.partner._columns
        old_all_columns = self.partner._all_columns
        self.partner._columns = dict(old_columns)
        self.partner._all_columns = dict(old_all_columns)
        self.partner._columns.update({
            'single_related_company_id': fields.related('company_id', type='many2one', obj='res.company'),
            'related_related_company_id': fields.related('single_related_company_id', type='many2one', obj='res.company'),
        })
        self.partner._all_columns.update({
            'single_related_company_id': fields.column_info('single_related_company_id', self.partner._columns['single_related_company_id'], None, None, None),
            'related_related_company_id': fields.column_info('related_related_company_id', self.partner._columns['related_related_company_id'], None, None, None)
        })

        self.do_test_company_field('related_related_company_id')

        # restore res.partner fields
        self.partner._columns = old_columns
        self.partner._all_columns = old_all_columns

    def test_3_read_write(self):
        """ write on a related field """
        # add a related field test_related_company_id on res.partner
        old_columns = self.partner._columns
        self.partner._columns = dict(old_columns)
        self.partner._columns.update({
            'related_company_partner_id': fields.related('company_id', 'partner_id', type='many2one', obj='res.partner'),
        })

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

        # restore res.partner fields
        self.partner._columns = old_columns


class TestPropertyField(common.TransactionCase):

    def setUp(self):
        super(TestPropertyField, self).setUp()
        self.user = self.registry('res.users')
        self.partner = self.registry('res.partner')
        self.company = self.registry('res.company')
        self.country = self.registry('res.country')
        self.property = self.registry('ir.property')
        self.imd = self.registry('ir.model.data')

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
        self.partner._all_columns.update({
            'property_country': fields.column_info('property_country', self.partner._columns['property_country'], None, None, None),
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
    <tr>
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

        self.partner._columns = old_columns
