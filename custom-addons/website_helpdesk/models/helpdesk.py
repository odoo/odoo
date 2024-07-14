# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.addons.http_routing.models.ir_http import slug


class HelpdeskTeam(models.Model):
    _name = "helpdesk.team"
    _inherit = ['helpdesk.team', 'website.published.mixin']

    feature_form_url = fields.Char('URL to Submit Issue', readonly=True, compute='_compute_form_url')
    website_id = fields.Many2one('website', domain="[('company_id', '=?', company_id)]", compute='_compute_website_id', store=True, readonly=False)
    website_menu_id = fields.Many2one('website.menu')
    website_form_view_id = fields.Many2one('ir.ui.view', string="Form")

    @api.constrains('use_website_helpdesk_form', 'website_id', 'company_id')
    def _check_website_company(self):
        if any(t.use_website_helpdesk_form and t.website_id and t.website_id.company_id != t.company_id for t in self):
            raise ValidationError(_('The team company and the website company should match'))

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
            team.website_url = "/helpdesk/%s" % slug(team)

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

    def action_view_all_rating(self):
        """ Override this method without calling parent to redirect to rating website team page """
        self.ensure_one()
        if not self.portal_show_rating:
            return super().action_view_all_rating()

        return {
            'type': 'ir.actions.act_url',
            'name': "Redirect to the Website Helpdesk Rating Page",
            'target': 'self',
            'url': "/helpdesk/rating/"
        }

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

        team_count_data = self.env['helpdesk.team']._read_group([
            ('use_website_helpdesk_form', '=', True),
        ], ['website_id'], ['__count', 'id:recordset'])
        team_count = {website.id: count for website, count, teams in team_count_data}

        for team in with_website:
            if not team.website_menu_id:
                parent_menu = team.website_id.menu_id
                if parent_menu:
                    menu = self.env['website.menu'].sudo().create({
                        'name': team.name if team_count.get(team.website_id.id, 0) > 1 else _('Help'),
                        'url': team.website_url,
                        'parent_id': parent_menu.id,
                        'sequence': 50,
                        'website_id': team.website_id.id,
                    })
                    team.website_menu_id = menu.id

        for team_count, teams in ((team_count, teams) for _, team_count, teams in team_count_data):
            # Rename team menu from "{Team Name}" -> "Help"
            if team_count == 1:
                team = teams.filtered(
                    lambda t: t.website_menu_id.name == t.name
                )
                if team:
                    team.website_menu_id.name = _('Help')
            # Rename team menu from "Help" -> "{Team Name}"
            elif team_count > 1:
                teams = teams.filtered(
                    lambda t: t.website_menu_id.name != t.name
                )
                for team in teams:
                    team.website_menu_id.name = team.name

    @api.depends('name', 'use_website_helpdesk_form', 'company_id')
    def _compute_form_url(self):
        for team in self:
            base_url = team.get_base_url()
            team.feature_form_url = (team.use_website_helpdesk_form and team.name and team.id) and (base_url + '/helpdesk/' + slug(team)) or False

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
            'helpdesk': slug(self),
            'max_date': self._helpcenter_date_from_search(searches),
            'tag': searches.get('tag', False),
        }

    def open_website_url(self):
        return self.env['website'].get_client_action(self.website_url, website_id=self.website_id.id)
