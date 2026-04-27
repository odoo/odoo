# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class HelpdeskTeam(models.Model):
    _name = "helpdesk.team"
    _inherit = ['helpdesk.team', 'website.published.mixin', 'website.seo.metadata']

    feature_form_url = fields.Char('URL to Submit Issue', readonly=True, compute='_compute_form_url', export_string_translation=False)
    website_id = fields.Many2one('website', domain="[('company_id', '=?', company_id)]", compute='_compute_website_id', store=True, readonly=False)
    website_menu_id = fields.Many2one('website.menu', export_string_translation=False)
    website_form_view_id = fields.Many2one('ir.ui.view', export_string_translation=False)

    @api.constrains('use_website_helpdesk_form', 'website_id', 'company_id')
    def _check_website_company(self):
        if any(t.use_website_helpdesk_form and t.website_id and t.website_id.company_id != t.company_id for t in self):
            raise ValidationError(_('The companies of the team and the website should match.'))

    @api.depends('company_id')
    def _compute_website_id(self):
        for team in self:
            team.website_id = team.company_id.website_id

    @api.model
    def _get_knowledge_base_fields(self):
        return []

    @api.depends(lambda self: ['use_website_helpdesk_form'] + [f for f in self._get_knowledge_base_fields()])
    def _compute_show_knowledge_base(self):
        kb_fields = self._get_knowledge_base_fields()
        for team in self:
            team.show_knowledge_base = team.use_website_helpdesk_form and any(team[field] for field in kb_fields)

    def _compute_website_url(self):
        super(HelpdeskTeam, self)._compute_website_url()
        for team in self:
            team.website_url = "/helpdesk/%s" % self.env['ir.http']._slug(team)

    @api.onchange('use_website_helpdesk_form', 'use_website_helpdesk_forum', 'use_website_helpdesk_slides', 'use_website_helpdesk_knowledge')
    def _onchange_use_website_helpdesk(self):
        if not (self.use_website_helpdesk_form or self.use_website_helpdesk_forum or self.use_website_helpdesk_slides or self.use_website_helpdesk_knowledge) and self.website_published:
            self.is_published = False
        elif self.use_website_helpdesk_form and not self.website_published:
            self.is_published = True

    def write(self, vals):
        if 'active' in vals and not vals['active']:
            vals['is_published'] = False
        res = super(HelpdeskTeam, self).write(vals)
        if 'use_website_helpdesk_form' in vals and vals['use_website_helpdesk_form']:
            self._ensure_submit_form_view()
        if {'use_website_helpdesk_form', 'is_published'} & vals.keys():
            self._ensure_website_menu()
        return res

    @api.model_create_multi
    def create(self, vals_list):
        teams = super(HelpdeskTeam, self).create(vals_list)
        teams.filtered('use_website_helpdesk_form')._ensure_submit_form_view()
        teams._ensure_website_menu()
        return teams

    def unlink(self):
        self.website_menu_id.unlink()
        return super(HelpdeskTeam, self).unlink()

    def _ensure_submit_form_view(self):
        teams = self.filtered('use_website_helpdesk_form')
        if not teams:
            return

        default_form = self.env.ref('website_helpdesk.ticket_submit_form').sudo().arch
        for team in teams:
            if not team.website_form_view_id:
                xmlid = 'website_helpdesk.team_form_' + str(team.id)
                form_template = self.env['ir.ui.view'].sudo().create({
                    'type': 'qweb',
                    'arch': default_form,
                    'name': xmlid,
                    'key': xmlid
                })
                self.env['ir.model.data'].sudo().create({
                    'module': 'website_helpdesk',
                    'name': xmlid.split('.')[1],
                    'model': 'ir.ui.view',
                    'res_id': form_template.id,
                    'noupdate': True
                })
                team.website_form_view_id = form_template.id

    def _ensure_website_menu(self):
        with_website = self.filtered_domain([('use_website_helpdesk_form', '=', True)])
        without_website = self - with_website
        without_website.website_menu_id.unlink()

        team_count_by_website = dict(
            self.env['helpdesk.team']._read_group(
                [('use_website_helpdesk_form', '=', True)],
                ['website_id'],
                ['__count'],
            )
        )
        teams_per_website = with_website.grouped('website_id')
        # process each website separately
        for website, teams in teams_per_website.items():
            if any(team.website_menu_id for team in teams):
                continue
            team_count = team_count_by_website.get(website.id, 0)
            if team_count <= 1:
                parent_menu = website.menu_id
                if parent_menu:
                    menu = self.env['website.menu'].sudo().create({
                        'name': _('Help'),
                        'url': '/helpdesk',
                        'parent_id': parent_menu.id,
                        'sequence': 50,
                        'website_id': website.id,
                    })
                    teams.website_menu_id = menu.id

    @api.depends('name', 'use_website_helpdesk_form', 'company_id')
    def _compute_form_url(self):
        for team in self:
            base_url = team.get_base_url()
            team.feature_form_url = (team.use_website_helpdesk_form and team.name and team.id) and (base_url + '/helpdesk/' + self.env['ir.http']._slug(team)) or False

    def _helpcenter_filter_types(self):
        return {}

    def _helpcenter_filter_tags(self, search_type):
        return []

    def _helpcenter_date_from_search(self, searches):
        if not searches.get('date'):
            return False

        delta = {'7days': 7, '30days': 30, '365days': 365}.get(searches['date'])
        if not delta:
            return False

        today = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
        return today - timedelta(days=delta)

    def get_knowledge_base_url(self):
        self.ensure_one()
        return self.feature_form_url

    def _get_search_options(self, searches):
        return {
            'displayDescription': True,
            'displayDetail': True,
            'displayExtraDetail': True,
            'displayExtraLink': True,
            'displayImage': False,
            'allowFuzzy': True,
            'helpdesk': self.env['ir.http']._slug(self),
            'max_date': self._helpcenter_date_from_search(searches),
            'tag': searches.get('tag', False),
        }

    def open_website_url(self):
        return self.env['website'].get_client_action(self.website_url, website_id=self.website_id.id)
