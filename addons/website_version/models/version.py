# -*- coding: utf-8 -*-
from openerp import fields, models, api
from openerp.exceptions import Warning
from openerp.http import request
from openerp.tools.translate import _


class version(models.Model):
    """ A version is a set of qweb views which differs from the qweb views in production for the website.
    """

    _name = "website_version.version"

    name = fields.Char(string="Title", required=True)
    view_ids = fields.One2many('ir.ui.view', 'version_id', string="View", copy=True)
    website_id = fields.Many2one('website', ondelete='cascade', string="Website")
    create_date = fields.Datetime('Create Date')

    _sql_constraints = [
        ('name_uniq', 'unique(name, website_id)', _('You cannot have multiple versions with the same name in the same domain!')),
    ]

    @api.multi
    def unlink(self):
        for id in self.ids:
            result = self.env['website_version.experiment'].search(['|', ('state', '=', 'running'), ('state', '=', 'paused'), ('experiment_version_ids.version_id', '=', id)])
            if result:
                raise Warning(_("You cannot delete a version which is in a running or paused experiment."))
        #To avoid problem when we delete versions in Backend
        if request:
            request.session['version_id'] = 0
        return super(version, self).unlink()

    @api.multi
    def action_publish(self):
        for version in self:
            self.view_ids.publish()

    @api.one
    def publish_version(self, save_master, copy_master_name):
        del_l = self.env['ir.ui.view']
        copy_l = self.env['ir.ui.view']
        ir_ui_view = self.env['ir.ui.view']
        for view in self.view_ids:
            master_id = ir_ui_view .search([('key', '=', view.key), ('version_id', '=', False), ('website_id', '=', view.website_id.id)])
            if master_id:
                #Delete all the website views having a key which is in the version published
                del_l += master_id
                copy_l += master_id
            else:
                #Views that have no website_id, must be copied because they can be shared with another website
                master_id = ir_ui_view.search([('key', '=', view.key), ('version_id', '=', False), ('website_id', '=', False)])
                copy_l += master_id
        if copy_l:
            if save_master:
                #To check if the name of the version to copy master already exists
                check_id = self.search([('name', '=', copy_master_name), ('website_id', '=', self.website_id.id)])
                #If it already exists, we delete the old to make the new
                if check_id:
                    check_id.unlink()
                copy_version_id = self.create({'name': copy_master_name, 'website_id': self.website_id.id})
                copy_l.copy({'version_id': copy_version_id.id, 'website_id': self.website_id.id})
            del_l.unlink()
        #All the views in the version published are copied without version_id
        for view in self.view_ids:
            view.copy({'version_id': None})
        return self.name

    #To make a version of a version
    @api.one
    def copy_version(self, new_version_id):
        for view in self.view_ids:
            view.copy({'version_id': new_version_id})

