# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests.common import TransactionCase, tagged
from collections import defaultdict
import logging
_logger = logging.getLogger(__name__)

@tagged('post_install', '-at_install')
class TestIrRules(TransactionCase):

    def test_print_acl_detect(self):
        """ Print the max of each (model, group) order by model name ASC for model and group name ASC
        It is usefull to detect a change of behavior (compare the diff) after a change in ACL
        """
        modes = ('read', 'write', 'create', 'unlink')
        models = self.env['ir.model'].sudo().search([], order="model")
        groups = self.env['res.groups'].sudo().search([], order="name")

        res = []
        for model in models:
            for group in groups:
                acls = model.access_ids & (group.model_access | group.transitive_access_ids)
                acl_max = [1 if max(acls.mapped(f"perm_{mode}"), default=False) else 0 for mode in modes]
                if acl_max != [0, 0, 0, 0]:
                    ir_data_group = self.env['ir.model.data'].search([('model', '=', 'res.groups'), ('res_id', '=', group.id)])
                    res.append(f"{model.model} - {ir_data_group.complete_name} : {acl_max}")
        print("ACL in file")
        with open("./odoo/acl_.txt", "w") as f:
            f.write("\n".join(sorted(res)))
        print("ACL in file done")
