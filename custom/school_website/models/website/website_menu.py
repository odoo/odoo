from odoo import models, api, fields
import logging

_logger = logging.getLogger(__name__)


class WebsiteMenu(models.Model):
    _inherit = 'website.menu'

    @api.model_create_multi
    def create(self, vals_list):
        if self.env.context.get('skip_school_website_menu_split'):
            return super().create(vals_list)

        default_menu = self.env.ref('website.main_menu', raise_if_not_found=False)
        websites = self.env['website'].search([])

        cleaned_vals_list = []
        for vals in vals_list:
            website_id = vals.get('website_id')
            parent_id = vals.get('parent_id')

            # If creating from XML data without website_id and parent is not website.main_menu
            if not website_id and parent_id and (not default_menu or parent_id != default_menu.id):
                parent_record = self.browse(parent_id)
                # Create website-specific copies attached to website's parent
                for website in websites:
                    site_parent = self.search([
                        ('website_id', '=', website.id),
                        ('name', '=', parent_record.name),
                    ], limit=1)
                    if not site_parent and parent_record.url:
                        site_parent = self.search([
                            ('website_id', '=', website.id),
                            ('url', '=', parent_record.url),
                        ], limit=1)

                    target_parent_id = site_parent.id if site_parent else website.menu_id.id
                    cleaned_vals_list.append({
                        **vals,
                        'website_id': website.id,
                        'parent_id': target_parent_id,
                    })

                # Also keep master template copy
                cleaned_vals_list.append({
                    **vals,
                    'website_id': False,
                    'parent_id': parent_id,
                })
            else:
                cleaned_vals_list.append(vals)

        return super().create(cleaned_vals_list)

    @api.model
    def sync_school_website_menus(self):
        """
        Reconcile and ensure Harvard University navigation menus are properly structured,
        cleanly nested, and free from orphaned or duplicate records across all websites.
        """
        self = self.with_context(skip_school_website_menu_split=True)
        default_menu = self.env.ref('website.main_menu', raise_if_not_found=False)

        menu_hierarchy = [
            {
                'name': 'Academics',
                'url': '#',
                'sequence': 10,
                'children': [
                    {'name': 'Degree Programs', 'url': '/courses', 'sequence': 10},
                    {'name': 'eLearning & Online Courses', 'url': '/slides', 'sequence': 20},
                ],
            },
            {
                'name': 'Apply Online',
                'url': '/admission/apply',
                'sequence': 20,
                'children': [],
            },
            {
                'name': 'Campus Life',
                'url': '#',
                'sequence': 30,
                'children': [
                    {'name': 'Campus Events', 'url': '/events', 'sequence': 10},
                    {'name': 'Student Forum', 'url': '/forum', 'sequence': 20},
                    {'name': 'News & Stories', 'url': '/blog', 'sequence': 30},
                    {'name': 'Bookstore & Shop', 'url': '/shop', 'sequence': 40},
                ],
            },
            {
                'name': 'About',
                'url': '#',
                'sequence': 40,
                'children': [
                    {'name': 'About Harvard', 'url': '/aboutus', 'sequence': 10},
                    {'name': 'Careers & Jobs', 'url': '/jobs', 'sequence': 20},
                    {'name': 'Contact Us', 'url': '/contactus', 'sequence': 30},
                ],
            },
        ]

        targets = []
        if default_menu:
            targets.append((False, default_menu))
        for website in self.env['website'].search([]):
            if website.menu_id:
                targets.append((website.id, website.menu_id))

        for site_id, root_menu in targets:
            domain_base = [('website_id', '=', site_id)] if site_id else [('website_id', '=', False)]

            # 1. Clean up orphaned submenus (submenus on website pointing to template parent)
            if site_id:
                orphans = self.search([
                    ('website_id', '=', site_id),
                    ('parent_id.website_id', '=', False),
                    ('parent_id', '!=', default_menu.id if default_menu else False),
                ])
                if orphans:
                    _logger.info("Cleaning up %d orphaned submenus for website %s", len(orphans), site_id)
                    orphans.unlink()

            # 2. Synchronize main menu groups and submenus
            for group_def in menu_hierarchy:
                group_menus = self.search(domain_base + [
                    ('parent_id', '=', root_menu.id),
                    ('name', '=', group_def['name']),
                ])

                if not group_menus and group_def['url'] != '#':
                    group_menus = self.search(domain_base + [
                        ('parent_id', '=', root_menu.id),
                        ('url', '=', group_def['url']),
                    ])

                vals = {
                    'name': group_def['name'],
                    'url': group_def['url'],
                    'parent_id': root_menu.id,
                    'sequence': group_def['sequence'],
                    'website_id': site_id,
                }
                if not group_menus:
                    group_menu = self.create(vals)
                else:
                    group_menu = group_menus[0]
                    if len(group_menus) > 1:
                        group_menus[1:].unlink()
                    group_menu.write(vals)

                # Synchronize child items
                child_ids = []
                for child_def in group_def['children']:
                    child_menus = self.search(domain_base + [
                        ('parent_id', '=', group_menu.id),
                        ('url', '=', child_def['url']),
                    ])

                    child_vals = {
                        'name': child_def['name'],
                        'url': child_def['url'],
                        'parent_id': group_menu.id,
                        'sequence': child_def['sequence'],
                        'website_id': site_id,
                    }
                    if not child_menus:
                        child_menu = self.create(child_vals)
                    else:
                        child_menu = child_menus[0]
                        if len(child_menus) > 1:
                            child_menus[1:].unlink()
                        child_menu.write(child_vals)
                    child_ids.extend(child_menu.ids)

                # Remove any stray child menus under this group not in definition
                stray_children = self.search(domain_base + [
                    ('parent_id', '=', group_menu.id),
                    ('id', 'not in', child_ids),
                ])
                if stray_children:
                    stray_children.unlink()

            # 3. Avoid duplicate root menus (e.g., standard /contactus, /shop, /blog at root)
            redundant_root_urls = {'/contactus', '/shop', '/blog', '/forum', '/slides', '/event', '/events', '/jobs', '/aboutus'}
            redundant_roots = self.search(domain_base + [
                ('parent_id', '=', root_menu.id),
                ('url', 'in', list(redundant_root_urls)),
            ])
            if redundant_roots:
                _logger.info("Removing redundant root menus on website %s: %s", site_id, redundant_roots.mapped('url'))
                redundant_roots.unlink()

        self.env.registry.clear_cache('templates')
        return True
