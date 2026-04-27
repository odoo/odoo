# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.point_of_sale.tests.common import TestPoSCommon
from odoo.tests import tagged
from odoo import Command


@tagged('post_install', '-at_install')
class TestPosPreparationDisplay(TestPoSCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = cls.basic_config

    def test_load_preparation_display_model(self):
        
        config1 = self.env['pos.config'].create({
            'name': 'rest1',
            'active': False
        })
        config2 = self.env['pos.config'].create({
            'name': 'rest2'
        })
        config3 = self.env['pos.config'].create({
            'name': 'rest3'
        })
        config4 = self.env['pos.config'].create({
            'name': 'rest4'
        })
        
        #pos preperation display linked to specific configs
        display1 = self.env['pos_preparation_display.display'].create({
            'name': 'Preparation Display 1',
            'pos_config_ids': [Command.link(config1.id)]
        })
        display2 = self.env['pos_preparation_display.display'].create({
            'name': 'Preparation Display 2',
            'pos_config_ids': [Command.link(config2.id)]
        })
        display3 = self.env['pos_preparation_display.display'].create({
            'name': 'Preparation Display 3',
            'pos_config_ids': []
        })
        display4 = self.env['pos_preparation_display.display'].create({
            'name': 'Preparation Display 4',
            'pos_config_ids': [Command.link(config3.id)]
        })
        
        config2.open_ui()
        config3.open_ui()
        config4.open_ui()
        
        self.assertEqual({d['id'] for d in config2.current_session_id.load_data([])['pos_preparation_display.display']['data']},
                         {display1.id, display2.id, display3.id})
        self.assertEqual({d['id'] for d in config3.current_session_id.load_data([])['pos_preparation_display.display']['data']},
                         {display1.id, display3.id, display4.id})
        self.assertEqual({d['id'] for d in config4.current_session_id.load_data([])['pos_preparation_display.display']['data']},
                         {display1.id, display3.id})
