import json

from odoo.tests import HttpCase, tagged
from odoo.tools import mute_logger

UNLINK_BLOCKED_ERROR = 'odoo.addons.web.models.models.UnlinkBlockedError'


@tagged('-at_install', 'post_install')
class TestWebUnlink(HttpCase):
    """ Test that `web_unlink()` (see `Base.web_unlink` in
    `addons/web/models/models.py`) turns a foreign key/RESTRICT violation
    into an `UnlinkBlockedError` enriched with the data the web client needs,
    and pinpoints - within a multi-record selection - exactly which records
    are the actual problem, without deleting anything for real, by retrying
    the deletion record by record once the initial bulk attempt has failed
    and been rolled back.

    That error's dotted name is what gets the web client to show its
    dedicated dialog, from wherever `web_unlink()` was called, with no
    per-view wiring: it is registered against `UnlinkBlockedErrorDialog` in
    `@web/core/errors/error_dialogs`. """

    def _web_unlink_over_http(self, records):
        self.authenticate('admin', 'admin')
        with mute_logger('odoo.sql_db', 'odoo.http'):
            return self.url_open('/web/dataset/call_kw', data=json.dumps({
                'params': {
                    'model': records._name,
                    'method': 'web_unlink',
                    'args': [records.ids],
                    'kwargs': {},
                },
            }), headers={'Content-Type': 'application/json'})

    def test_not_archivable(self):
        # res.country.state has no 'active'/'x_active' field
        country = self.env.ref('base.us')
        state = self.env['res.country.state'].create({
            'name': 'Test State', 'code': 'TS', 'country_id': country.id,
        })
        self.env['res.partner'].create({'name': 'Partner', 'state_id': state.id, 'country_id': country.id})

        error = self._web_unlink_over_http(state).json()['error']

        self.assertEqual(error['data']['name'], UNLINK_BLOCKED_ERROR)
        self.assertEqual(error['data']['context'], {
            'archivable': False,
            'model_name': 'Contact',
            'res_model': 'res.country.state',
            'res_ids': [state.id],
            'blocked_ids': [state.id],
        })
        self.assertTrue(state.exists())

    def test_archivable(self):
        # res.company has an 'active' field
        parent = self.env['res.company'].create({'name': 'Parent Co'})
        self.env['res.company'].create({'name': 'Child Co', 'parent_id': parent.id})

        error = self._web_unlink_over_http(parent).json()['error']
        context = error['data']['context']

        self.assertEqual(error['data']['name'], UNLINK_BLOCKED_ERROR)
        # which of a company's dependants is reported depends on the installed
        # modules, so only `test_not_archivable` asserts `model_name`
        self.assertEqual({key: value for key, value in context.items() if key != 'model_name'}, {
            'archivable': True,
            'res_model': 'res.company',
            'res_ids': [parent.id],
            'blocked_ids': [parent.id],
        })
        self.assertTrue(context['model_name'])
        self.assertTrue(parent.exists())

    def test_pinpoints_blocked_ids_within_bulk_selection(self):
        """ Among a bulk selection, only the record(s) that actually block
        the delete are reported in `blocked_ids` - `res_ids` keeps the whole
        selection, which "Archive" still acts on - and, per the all-or-nothing
        semantics of unlink(), neither record actually gets deleted. """
        country = self.env.ref('base.us')
        State = self.env['res.country.state']
        blocked = State.create({'name': 'Blocked State', 'code': 'TB', 'country_id': country.id})
        free = State.create({'name': 'Free State', 'code': 'TF', 'country_id': country.id})
        self.env['res.partner'].create({'name': 'Partner', 'state_id': blocked.id, 'country_id': country.id})

        context = self._web_unlink_over_http(blocked + free).json()['error']['data']['context']

        self.assertEqual(context['res_ids'], (blocked + free).ids)
        self.assertEqual(context['blocked_ids'], [blocked.id])
        self.assertTrue(blocked.exists())
        self.assertTrue(free.exists())
