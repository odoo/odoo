import openerp.tests
from openerp import SUPERUSER_ID
@openerp.tests.common.at_install(False)
@openerp.tests.common.post_install(True)
class TestFormBuilder(openerp.tests.HttpCase):
    def test_tour(self):
        self.phantom_js("/", "openerp.Tour.run('website_form_builder_tour', 'test')", "openerp.Tour.tours.website_form_builder_tour", login="admin")

    def test_data_inserted(self):
        mail = self.registry('mail.mail').search_read(self.cr, SUPERUSER_ID,
            [('body_html', 'like', 'My more usless message'),
             ('body_html', 'like', 'Service : S.F.'),
             ('body_html', 'like', 'State : be'),
             ('body_html', 'like', 'Products : galaxy S, Xperia')])

        lead = self.registry('crm.lead').search_read(self.cr, SUPERUSER_ID,
            [('contact_name', '='   , 'John Smith'),
             ('phone'       , '='   , '118.218'),
             ('email_from'  , '='   , 'john@smith.com'),
             ('name'        , '='   , 'Usless Message'),
             ('description' , 'like', 'The complete usless Message')])

        appl = self.registry('hr.applicant').search_read(self.cr, SUPERUSER_ID,
            [('partner_name'    , '='   , 'John Smith'),
             ('partner_phone'   , '='   , '118.218'),
             ('email_from'      , '='   , 'john@smith.com'),
             ('description'     , 'like', 'The complete usless Message')])

        self.assertNotEqual(mail, [], 'ERROR :: mail not inserted');
        self.assertNotEqual(lead, [], 'ERROR :: lead not inserted');
        self.assertNotEqual(appl, [], 'ERROR :: appl not inserted');

