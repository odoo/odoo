# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class Project(models.Model):

    _name = "project.project"
    _inherit = ['project.project', 'website.published.mixin']

    @api.multi
    def action_view_all_rating(self):
        """ Override this method without calling parent to redirect to rating website project page """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'name': "Redirect to the Website Projcet Rating Page",
            'target': 'self',
            'url': "/project/rating/%s" % (self.id,)
        }

    @api.multi
    def _compute_website_url(self):
        super(Project, self)._compute_website_url()
        for project in self:
            project.website_url = "/project/rating/%s" % project.id


class ProjectTask(models.Model):
    _inherit = 'project.task'

    def _get_top_five_rated_partners_task(self, project_id):
        current_project_id = project_id
        self.env.cr.execute("""SELECT project_id,rating_rating.rated_partner_id,count(rating_rating.rating) as partner_id_count,res_partner.name,
            count (rating_rating.rating) * 100.00/(select count(rating_rating.rating) from rating_rating,project_task where project_task.project_id=%s and project_task.id = rating_rating.res_id) as rating_percentage,
            sum(CASE WHEN rating_rating.rating=1 then 1 END) as unhappy,
            sum(CASE WHEN rating_rating.rating=5 then 1 END) as okay,
            sum(CASE WHEN rating_rating.rating=10 then 1 END) as happy
            from project_task left join rating_rating on project_task.id = rating_rating.res_id
            left join res_partner on rating_rating.rated_partner_id = res_partner.id
            where rating_last_value != 0 and project_id=%s and rating_rating.write_date > current_date - interval '15' day
            GROUP BY project_id,rating_rating.rated_partner_id,res_partner.name
            ORDER BY partner_id_count desc, res_partner.name asc limit 5;""" % (current_project_id, current_project_id))
        all_record = self.env.cr.dictfetchall()
        return {'all_record': all_record}


class ProjectIssue(models.Model):
    _inherit = 'project.issue'

    def _get_top_five_rated_partners_issue(self, project_id):
        current_project_id = project_id
        self.env.cr.execute("""SELECT project_id,rating_rating.rated_partner_id,count(rating_rating.rating) as partner_id_count,res_partner.name,
            count (rating_rating.rating) * 100.00/(select count(rating_rating.rating) from rating_rating,project_issue where project_issue.project_id=%s and project_issue.id =rating_rating.res_id) as rating_percentage,
            sum(CASE WHEN rating_rating.rating=1 then 1 END) as unhappy,
            sum(CASE WHEN rating_rating.rating=5 then 1 END) as okay,
            sum(CASE WHEN rating_rating.rating=10 then 1 END) as happy
            from project_issue left join rating_rating on project_issue.id = rating_rating.res_id
            left join res_partner on rating_rating.rated_partner_id = res_partner.id
            where rating_last_value != 0 and project_id=%s and rating_rating.write_date > current_date - interval '15' day
            GROUP BY project_id,rating_rating.rated_partner_id,res_partner.name
            ORDER BY partner_id_count desc, res_partner.name asc limit 5;""" % (current_project_id, current_project_id))
        all_record = self.env.cr.dictfetchall()
        return {'all_record': all_record}
