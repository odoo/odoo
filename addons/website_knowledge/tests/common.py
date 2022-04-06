# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.knowledge.tests.common import KnowledgeCommonWData


class WKnowledgeCommonWData(KnowledgeCommonWData):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # - Playground (workspace, writable)
        #   - Child1
        #   - Child2
        # - Private (shared)
        #   - Child1
        #   - ChildPublished
        cls.shared_children += cls.env['knowledge.article'].create([
            {'article_member_ids': [
                (0, 0, {'partner_id': cls.partner_admin.id,
                        'permission': 'write',
                       }),
             ],
             'internal_permission': 'none',
             'is_published': True,
             'name': 'Private Child1',
             'parent_id': cls.article_shared.id,
            }
        ])
