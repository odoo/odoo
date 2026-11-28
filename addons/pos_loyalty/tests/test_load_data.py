# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.pos_loyalty.tests.common import CommonPosLoyaltyTest


@tagged('-at_install', 'post_install')
class TestPosLoyaltyLoadData(CommonPosLoyaltyTest):

    def test_removed_programs_are_removed_from_local_data(self):
        """Programs cached by the PoS (IndexedDB) that were archived, deleted or are no
        longer available to it must be listed in `to_remove` on the next load."""
        config = self.pos_config_usd
        archived_program = self.four_20_dollars_one_free_program
        deleted_program, unpublished_program = self.env['loyalty.program'].create([{
            'name': name,
            'program_type': 'promotion',
            'trigger': 'auto',
            'applies_on': 'current',
            'rule_ids': [Command.create({'minimum_qty': 1})],
            'reward_ids': [Command.create({
                'reward_type': 'discount',
                'discount': 10,
                'discount_mode': 'percent',
                'discount_applicability': 'order',
            })],
        } for name in ('Deleted promotion', 'Unpublished promotion')])
        programs = archived_program | deleted_program | unpublished_program
        self.assertEqual(programs & config._get_program_ids(), programs)
        config.open_ui()
        session = config.current_session_id
        local_records = {
            'loyalty.program': {
                str(program.id): int(program.write_date.timestamp()) for program in programs
            },
        }
        deleted_program_id = deleted_program.id

        archived_program.action_archive()
        deleted_program.action_archive()
        deleted_program.unlink()
        unpublished_program.pos_ok = False

        data = session.load_data({'models': ['loyalty.program'], 'records': local_records})
        to_remove = data['loyalty.program'].get('to_remove', [])
        self.assertIn(unpublished_program.id, to_remove, "An unpublished program must be removed")
        self.assertIn(archived_program.id, to_remove, "An archived program must be removed")
        self.assertIn(deleted_program_id, to_remove, "A deleted program must be removed")
