# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import MailCommon, mail_new_test_user
from odoo.tools import mute_logger


class KnowledgeCommon(MailCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_portal = cls._create_portal_user()
        cls.partner_portal = cls.user_portal.partner_id

        cls.user_employee_manager = mail_new_test_user(
            cls.env,
            company_id=cls.company_admin.id,
            country_id=cls.env.ref('base.be').id,
            groups='base.group_user',
            login='employee_manager',
            name='Evelyne Employee',
            notification_type='inbox',
            signature='--\nEvelyne'
        )
        cls.partner_employee_manager = cls.user_employee_manager.partner_id
        cls.user_employee2 = mail_new_test_user(
            cls.env,
            company_id=cls.company_admin.id,
            country_id=cls.env.ref('base.be').id,
            groups='base.group_user',
            login='employee2',
            name='Eglantine Employee',
            notification_type='inbox',
            signature='--\nEglantine'
        )
        cls.partner_employee2 = cls.user_employee2.partner_id

        cls.user_public = mail_new_test_user(
            cls.env,
            company_id=cls.company_admin.id,
            groups='base.group_public',
            login='user_public',
            name='Public Anonymous',
        )
        cls.partner_public = cls.user_public.partner_id

        cls.customer = cls.env['res.partner'].create({
            'country_id': cls.env.ref('base.be').id,
            'email': 'corentine@test.example.com',
            'mobile': '+32455001122',
            'name': 'Corentine Customer',
            'phone': '+32455334455',
        })

    def assertMembers(self, articles, exp_internal_permission, exp_partners_permissions, msg=None):
        """ Custom assert for members, to ease writing tests. Check state of
        members on articles, as sudo to avoid ACLs-based misunderstanding.

        :param internal_permission: global internal permission of articles;
        :param partners_permission: dict of pid: permission that are members
          expected to be on articles;
        """
        for article in articles.sudo():
            self.assertEqual(article.internal_permission, exp_internal_permission)
            self.assertEqual(
                dict(
                    (member.partner_id, member.permission)
                    for member in article.article_member_ids
                ),
                exp_partners_permissions,
                msg
            )

    def assertSortedSequence(self, articles):
        """ Assert that the articles are properly sorted according to their sequence
        number

        :param articles (Model<knowledge.article>): Recordset of knowledge.article
        """
        for k in range(len(articles) - 1):
            self.assertTrue(
                articles[k].sequence <= articles[k + 1].sequence,
                f'Article sequence issue: {articles[k].name} ({articles[k].sequence}) which is not <= than {articles[k + 1].name} ({articles[k + 1].sequence})')

    def _create_private_article(self, name, target_user=None):
        """ Due to membership model constraints, create test records as sudo
        and return a record in current user environment. Creation itself is
        not tested here. """
        target_user = self.env.user if target_user is None else target_user
        if target_user:
            vals = {
                'article_member_ids': [(0, 0, {
                    'partner_id': target_user.partner_id.id,
                    'permission': 'write',
                })],
            }
        vals.update({
            'internal_permission': 'none',
            'name': name,
            })
        return self.env['knowledge.article'].sudo().create(vals).with_user(self.env.user)

    def _create_cover(self):
        pixel = 'R0lGODlhAQABAIAAAP///wAAACwAAAAAAQABAAACAkQBADs='
        attachment = self.env['ir.attachment'].create({'name': 'pixel', 'datas': pixel, 'res_model': 'knowledge.cover', 'res_id': 0})
        return self.env['knowledge.cover'].create({'attachment_id': attachment.id})


class KnowledgeCommonWData(KnowledgeCommon):
    """ Light setup of articles for knowledge tests. It holds data for the
    three main categories: workspace, shared and private articles. Some
    children exist to have some permission tweaks. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with mute_logger('odoo.models.unlink'):
            cls.env['knowledge.article'].search([]).unlink()

        # - Private         seq=997   private      none    (manager-w+)
        #   - Child1        seq=0     "            "
        # - Shared          seq=998   shared       none    (admin-w+,employee-r+,manager-r+)
        #   - Child1        seq=0     "            "       (employee-w+)
        #   - Child2        seq=0     "            "       (portal-r+)
        # - Playground      seq=999   workspace    w+
        #   - Child1        seq=0     "            "
        #   - Child2        seq=1     "            "
        cls._base_sequence = 999
        cls.article_workspace = cls.env['knowledge.article'].create(
            {'internal_permission': 'write',
             'favorite_ids': [(0, 0, {'sequence': 1,
                                      'user_id': cls.user_admin.id
                                     }),
             ],
             'name': 'Playground',
             'sequence': cls._base_sequence,
             'is_article_visible_by_everyone': True,
            }
        )
        cls.workspace_children = cls.env['knowledge.article'].create([
            {'name': 'Playground Child1',
             'parent_id': cls.article_workspace.id,
            },
            {'name': 'Playground Child2',
             'parent_id': cls.article_workspace.id,
            },
        ])
        cls.article_shared = cls.env['knowledge.article'].create(
            {'article_member_ids': [
                (0, 0, {'partner_id': cls.partner_admin.id,
                        'permission': 'write',
                       }),
                (0, 0, {'partner_id': cls.partner_employee.id,
                        'permission': 'read',
                       }),
                (0, 0, {'partner_id': cls.partner_employee_manager.id,
                        'permission': 'read',
                       }),
             ],
             'internal_permission': 'none',
             'name': 'Shared',
             'sequence': cls._base_sequence - 1,
            }
        )
        cls.shared_children = cls.env['knowledge.article'].create([
            {'article_member_ids': [
                (0, 0, {'partner_id': cls.partner_employee.id,
                        'permission': 'write',
                       }),
             ],
             'internal_permission': False,
             'name': 'Shared Child1',
             'parent_id': cls.article_shared.id,
            },
            {'article_member_ids': [
                (0, 0, {'partner_id': cls.partner_portal.id,
                        'permission': 'read',
                       }),
             ],
             'internal_permission': False,
             'favorite_ids': [
                (0, 0, {'sequence': 1,
                        'user_id': cls.user_portal.id,
                       }),
             ],
             'name': 'Shared Child2',
             'parent_id': cls.article_shared.id,
            }
        ])
        cls.article_private_manager = cls.env['knowledge.article'].create(
            {'article_member_ids': [
                (0, 0, {'partner_id': cls.partner_employee_manager.id,
                        'permission': 'write',
                       }),
             ],
             'internal_permission': 'none',
             'name': 'Private',
             'sequence': cls._base_sequence - 2,
            }
        )
        cls.private_children = cls.env['knowledge.article'].create([
            {'internal_permission': False,
             'name': 'Private Child1',
             'parent_id': cls.article_private_manager.id,
            }
        ])
        cls.env.flush_all()


class KnowledgeArticlePermissionsCase(KnowledgeCommon):
    """ Specific test class to test permission management, inheritance and
    computation on article model, based on both article and member permissions.
    This does not really test ACLs, more the internals of permissions that
    are used afterwards in ACLs and in various business methods / flows. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with mute_logger('odoo.models.unlink'):
            cls.env['knowledge.article'].search([]).unlink()

        # ------------------------------------------------------------
        #                         Perm (" = inherited) + exceptions
        # WRITABLE ROOT           write
        # - Community             " (w)
        #   - Members             " (w)   (-employee-read)
        #   - Readonly            read    (+manager-write)
        #   - Writable            " (w)   (+portal-read)
        #     - Writable child    " (w)
        #       - Child           "
        #     - Nyarlathotep      DESYNC  read, manager-write
        #       - Child           "
        # READABLE ROOT           read    (+manager-write)
        # - TTRPG                 " (r)
        #   - OpenCthulhu         write   (+portal-read)
        #     - MansionsOfTerror  DESYNC  none, employee-write, manager-read
        #       - Child           "
        #   - OpenParanoïa        write   (-employee-read, +portal-read)
        #   - Proprietary         " (r)
        #   - Secret              none
        #     - Child             "
        # - Board Games           " (r)
        # SHARED ROOT             none    (+manager-write, +employee-read)
        # PRIVATE ROOT            none    (+employee-write)
        #
        # ------------------------------------------------------------
        cls.article_roots = cls.env['knowledge.article'].create([
            {'name': 'Writable Root',
             'is_article_visible_by_everyone': True,
            },
            {'article_member_ids': [
                (0, 0, {'partner_id': cls.partner_employee_manager.id,
                        'permission': 'write',
                       }),
             ],  # ensure at least one write access
             'internal_permission': 'read',
             'name': 'Readable Root',
             'is_article_visible_by_everyone': True,
            },
            {'article_member_ids': [
                (0, 0, {'partner_id': cls.partner_employee_manager.id,
                        'permission': 'write',
                       }),
                (0, 0, {'partner_id': cls.partner_employee.id,
                        'permission': 'read',
                       }),
             ],
             'internal_permission': 'none',
             'favorite_ids': [
                (0, 0, {'user_id': cls.user_employee_manager.id}),
                (0, 0, {'user_id': cls.user_employee.id})
             ],
             'name': 'Shared Root',
            },
            {'article_member_ids': [
                (0, 0, {'partner_id': cls.partner_employee.id,
                        'permission': 'write',
                       }),
             ],
             'internal_permission': 'none',
             'name': 'Private Root',
            }
        ])
        cls.article_headers = cls.env['knowledge.article'].create([
            # writable
            {'name': 'Write-Community',
             'parent_id': cls.article_roots[0].id,
            },
            # readable
            {'name': 'Read-TTRPG',
             'parent_id': cls.article_roots[1].id,
            },
            {'name': 'Read-Board Games',
             'parent_id': cls.article_roots[1].id,
            },
        ])
        # Under Write internal permission
        cls.article_write_contents = cls.env['knowledge.article'].create([
            {'article_member_ids': [
                (0, 0, {'partner_id': cls.partner_employee.id,
                        'permission': 'read',
                       }),
             ],
             'favorite_ids': [
                (0, 0, {'user_id': cls.user_admin.id}),
                (0, 0, {'user_id': cls.user_employee.id})
             ],
             'name': 'Members Subarticle',
             'parent_id': cls.article_headers[0].id,
            },
            {'article_member_ids': [
                (0, 0, {'partner_id': cls.partner_employee_manager.id,
                        'permission': 'write',
                       }),
             ],  # ensure at least one write access
             'internal_permission': 'read',
             'name': 'Readonly Subarticle',
             'parent_id': cls.article_headers[0].id,
            },
            {'article_member_ids': [
                (0, 0, {'partner_id': cls.partner_portal.id,
                        'permission': 'read',
                       }),
             ],
             'body': '<p>Writable Subarticle through inheritance</p>',
             'favorite_ids': [
                (0, 0, {'user_id': cls.user_admin.id}),
                (0, 0, {'user_id': cls.user_employee.id}),
                (0, 0, {'user_id': cls.user_portal.id}),
             ],
             'name': 'Writable Subarticle through inheritance',
             'parent_id': cls.article_headers[0].id,
            },
        ])
        cls.article_write_contents_children = cls.env['knowledge.article'].create([
            {'name': 'Child of writable through inheritance',
             'parent_id': cls.article_write_contents[2].id,
            },
        ])
        cls.article_write_contents_children += cls.env['knowledge.article'].create([
            {'name': 'Child of child of writable through inheritance',
             'parent_id': cls.article_write_contents_children[0].id,
            },
        ])
        cls.article_write_desync = cls.env['knowledge.article'].create([
            # Community/Writable
            {'article_member_ids': [
                (0, 0, {'partner_id': cls.partner_employee_manager.id,
                        'permission': 'write',
                       }),
             ],
             'internal_permission': 'read',
             'is_desynchronized': True,
             'name': 'Desync Nyarlathotep',
             'parent_id': cls.article_write_contents[2].id,
            },
        ])
        cls.article_write_desync += cls.env['knowledge.article'].create([
            {'name': 'Childof Desync Nyarlathotep',
             'parent_id': cls.article_write_desync[0].id,
            },
        ])

        # Under Read internal permission
        cls.article_read_contents = cls.env['knowledge.article'].create([
            # TTRPG
            {'article_member_ids': [
                (0, 0, {'partner_id': cls.partner_portal.id,
                        'permission': 'read',
                       }),
             ],
             'internal_permission': 'write',
             'name': 'OpenCthulhu',
             'parent_id': cls.article_headers[1].id,
            },
            {'article_member_ids': [
                (0, 0, {'partner_id': cls.partner_portal.id,
                        'permission': 'read',
                       }),
                (0, 0, {'partner_id': cls.partner_employee.id,
                        'permission': 'read',
                       }),
             ],
             'internal_permission': 'write',
             'name': 'Open Paranoïa',
             'parent_id': cls.article_headers[1].id,
            },
            {'name': 'Proprietary RPGs',
             'parent_id': cls.article_headers[1].id,
            },
            {'internal_permission': 'none',
             'name': 'Secret RPGs',
             'parent_id': cls.article_headers[1].id,
            },
        ])
        cls.article_read_contents_children = cls.env['knowledge.article'].create([
            {'name': 'Child of Secret RPGs',
             'parent_id': cls.article_read_contents[3].id,
            },
        ])
        cls.article_read_desync = cls.env['knowledge.article'].create([
            # Read/TTRPG: Open Cthulhu
            {'article_member_ids': [
                (0, 0, {'partner_id': cls.partner_employee.id,
                        'permission': 'write',
                       }),
                (0, 0, {'partner_id': cls.partner_employee_manager.id,
                        'permission': 'read',
                       }),
             ],
             'internal_permission': 'none',
             'is_desynchronized': True,
             'name': 'Mansions of Terror',
             'parent_id': cls.article_read_contents[0].id,
            },
        ])
        cls.article_read_desync += cls.env['knowledge.article'].create([
            {'name': 'Childof Desync Mansions',
             'parent_id': cls.article_read_desync[0].id,
            },
        ])

        cls.articles_all = cls.article_roots + cls.article_headers + \
                           cls.article_write_contents + cls.article_write_contents_children + \
                           cls.article_read_contents + cls.article_read_contents_children + \
                           cls.article_write_desync + cls.article_read_desync
        cls.env.flush_all()
