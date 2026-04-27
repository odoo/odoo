# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time


from odoo import Command
from .test_common import TestQualityCommon
from odoo.addons.spreadsheet_edition.tests.spreadsheet_test_case import (
    SpreadsheetTestCase,
)


class TestQualitySpreadsheet(TestQualityCommon, SpreadsheetTestCase):

    def test_create_spreadsheet_template(self):
        spreadsheet = self.env['quality.spreadsheet.template'].create({
            'check_cell': 'A1',
            'name': 'my spreadsheet quality check template',
        })
        point = self.env['quality.point'].create({
            'name': 'QP1',
            'test_type_id': self.env.ref('quality_control.test_type_spreadsheet').id,
            'spreadsheet_template_id': spreadsheet.id,
            'picking_type_ids': [Command.link(self.picking_type_id)],
        })
        self.assertEqual(point.spreadsheet_check_cell, 'A1')
        data = spreadsheet.join_spreadsheet_session()
        self.assertEqual(data['quality_check_cell'], 'A1')

        picking = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_id,
            'partner_id': self.partner_id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id,
        })
        self.env['stock.move'].create({
            'name': self.product.name,
            'product_id': self.product.id,
            'product_uom_qty': 1,
            'product_uom': self.product.uom_id.id,
            'picking_id': picking.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id
        })
        picking.action_confirm()
        self.assertEqual(len(picking.check_ids), 1)
        check = picking.check_ids

        self.assertFalse(check.spreadsheet_id, "the spreadsheet is lazily created")
        action = check.action_open_spreadsheet()
        spreadsheet = check.spreadsheet_id
        self.assertEqual(action['params']['check_id'], check.id)
        self.assertEqual(action['params']['spreadsheet_id'], spreadsheet.id)

        data = spreadsheet.join_spreadsheet_session()
        self.assertEqual(data['quality_check_cell'], 'A1')

        check.unlink()
        self.assertFalse(spreadsheet.exists())

    def test_delete_history_after_inactivity(self):
        with freeze_time("2018-01-01"):
            spreadsheet = self.env["quality.check.spreadsheet"].create({
                'name': 'My spreadsheet',
                'check_cell': 'A1',
            })
            spreadsheet.dispatch_spreadsheet_message(
                self.new_revision_data(spreadsheet)
            )
            snapshot = {"revisionId": "next-revision"}
            self.snapshot(
                spreadsheet, spreadsheet.current_revision_uuid, "next-revision", snapshot
            )
            revisions = spreadsheet.with_context(
                active_test=False
            ).spreadsheet_revision_ids
            # write_date is not mocked when archiving, so we need to set it manually
            revisions.write_date = "2018-01-01"

            # the same day, the history is still there
            self.env["quality.check.spreadsheet"]._gc_spreadsheet_history()
            self.assertTrue(
                spreadsheet.with_context(active_test=False).spreadsheet_revision_ids
            )

        # the next day, the history is still there
        with freeze_time("2018-01-02"):
            self.env["quality.check.spreadsheet"]._gc_spreadsheet_history()
            self.assertFalse(
                spreadsheet.with_context(active_test=False).spreadsheet_revision_ids
            )
