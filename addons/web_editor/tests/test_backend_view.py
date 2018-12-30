from openerp.api import Environment
import openerp.tests

@openerp.tests.common.at_install(False)
@openerp.tests.common.post_install(True)
class TestBackendView(openerp.tests.HttpCase):

    def test_01_rte_backend_inline(self):
        """ Test saving inline editor in or out of code view mode. """
        with self.registry.cursor() as test_cursor:
            env = Environment(test_cursor, self.uid, {})
            test_record = env['web_editor.converter.test'].create({'html': '<p>hello </p>'})
            form_url = "/web?debug#id={}&view_type=form&model=web_editor.converter.test".format(test_record.id)

        self.phantom_js(form_url, "odoo.__DEBUG__.services['web.Tour'].run('rte_backend_inline', 'test')", "odoo.__DEBUG__.services['web.Tour'].tours.rte", login="admin")
