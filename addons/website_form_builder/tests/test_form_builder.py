import openerp.tests
from openerp import SUPERUSER_ID
@openerp.tests.common.at_install(False)
@openerp.tests.common.post_install(True)
class TestFormBuilder(openerp.tests.HttpCase):
    def test_tour(self):
        self.phantom_js("/", "openerp.Tour.run('website_form_builder_tour', 'test')", "openerp.Tour.tours.website_form_builder_tour", login="admin")
        mail = self.registry('mail.mail').search_read(self.cr, SUPERUSER_ID,
            [('body_html', 'like', 'My more usless message'),
             ('body_html', 'like', 'Service : S.F.'),
             ('body_html', 'like', 'State : be'),
             ('body_html', 'like', 'Products : galaxy S,Xperia')])

        print '\n[WEBSITE_FORM_BUILDER] ', mail,'\n'

        lead = self.registry('crm.lead').search_read(self.cr, SUPERUSER_ID,
            [('contact_name', '='   , 'John Smith'),
             ('phone'       , '='   , '118.218'),
             ('email_from'  , '='   , 'john@smith.com'),
             ('name'        , '='   , 'Usless Message'),
             ('description' , 'like', 'The complete usless Message')])

        print '\n[WEBSITE_FORM_BUILDER] ', lead,'\n'

        appl = self.registry('hr.applicant').search_read(self.cr, SUPERUSER_ID,
            [('partner_name'    , '='   , 'John Smith'),
             ('partner_phone'   , '='   , '118.218'),
             ('email_from'      , '='   , 'john@smith.com'),
             ('description'     , 'like', 'The complete usless Message')])

        print '\n[WEBSITE_FORM_BUILDER] ', appl,'\n'

        
        self.assertNotEqual(lead, [], 'ERROR :: lead not inserted')
        self.assertNotEqual(appl, [], 'ERROR :: appl not inserted')
        self.assertNotEqual(mail, [], 'ERROR :: mail not inserted')