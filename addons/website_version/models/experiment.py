# -*- coding: utf-8 -*-

from openerp.exceptions import Warning
from openerp import models, fields, api
from openerp.exceptions import ValidationError
from openerp.tools.translate import _

TOO_MUCH_EXPERIMENTS = 2
OVERLAP_EXPERIMENT = 1
CREATE_EXPERIMENT = 0


class Experiment_version(models.Model):
    """ Allow to define the versions contained in an experiment.
    The frequency is a ponderation to determine the probability to visit a version in an experiment.
    The googe_index is the index of a version in an experiment, used to send data to Google Analytics.
    """

    _name = "website_version.experiment.version"
    _rec_name = "version_id"

    version_id = fields.Many2one('website_version.version', string="Version", required=True, ondelete='cascade')
    experiment_id = fields.Many2one('website_version.experiment', string="Experiment", required=True, ondelete='cascade')
    frequency = fields.Selection([('10', 'Less'), ('50', 'Medium'), ('80', 'More')], string='Frequency', default='50')
    google_index = fields.Integer(string='Google index')


class Goals(models.Model):
    """ Allow to define the goal of an experiment.
    The goals are defined in the Google Analytics account and can be synchronised in backend.
    """
    _name = "website_version.goals"

    name = fields.Char(string="Name", required=True)
    google_ref = fields.Char(string="Google Reference", required=True)


class Experiment(models.Model):
    """An experiment pointed to some experiment_versions and dispatch each website visitor to a version.
    """

    _name = "website_version.experiment"
    _inherit = ['mail.thread']
    _order = 'sequence'

    @api.multi
    @api.constrains('state')
    def _check_view(self):
        #No overlap for running experiments
        for exp in self:
            if exp.state == 'running':
                for exp_ver in exp.experiment_version_ids:
                    if exp_ver.search([('version_id.view_ids.key', 'in', [v.key for v in exp_ver.version_id.view_ids]), ('experiment_id', '!=', exp_ver.experiment_id.id), ('experiment_id.website_id', '=', exp_ver.experiment_id.website_id.id), ('experiment_id.state', '=', 'running')]):
                        raise ValidationError('This experiment contains a view which is already used in another running experience')
        return True

    @api.multi
    @api.constrains('website_id', 'experiment_version_ids')
    def _check_website(self):
        for exp in self:
            for exp_ver in exp.experiment_version_ids:
                if not exp_ver.version_id.website_id.id == exp.website_id.id:
                    raise ValidationError('This experiment must have versions which are in the same website')

    _group_by_full = {
        'state': lambda *args, **kwargs: ([('running', 'Running'), ('paused', 'Paused'), ('ended', 'Ended')], dict())
    }

    @api.one
    def _get_version_number(self):
        for exp in self:
            exp.version_number = len(exp.experiment_version_ids) + 1

    name = fields.Char(string="Title", required=True)
    experiment_version_ids = fields.One2many('website_version.experiment.version', 'experiment_id', string="Experiment Version")
    website_id = fields.Many2one('website', string="Website", required=True)
    state = fields.Selection([('running', 'Running'), ('paused', 'Paused'), ('ended', 'Ended')], 'Status', required=True, copy=False, track_visibility='onchange', default='running')
    goal_id = fields.Many2one('website_version.goals', string="Objective", required=True)
    color = fields.Integer('Color Index')
    version_number = fields.Integer(compute=_get_version_number, string='Version Number')
    sequence = fields.Integer('Sequence', required=True, default=1)
    google_id = fields.Char(string="Google id")

    @api.model
    def create(self, vals):
        exp = {
            'name': vals['name'],
            'objectiveMetric': self.env['website_version.goals'].browse([vals['goal_id']])[0].google_ref,
            'status': vals['state'],
            'variations': [{'name': 'master', 'url': 'http://localhost/master'}]
        }
        version_list = vals.get('experiment_version_ids', [])
        for version in version_list:
            if version[0] == 0:
                name = self.env['website_version.version'].browse([version[2]['version_id']])[0].name
                #We must give a URL for each version in the experiment
                exp['variations'].append({'name': name, 'url': 'http://localhost/' + name})
            else:
                raise Warning(_("The experiment you try to create has a bad format."))
        if not version_list:
            raise Warning(_("You must select at least one version in your experiment."))
        vals['google_id'] = self.env['google.management'].create_an_experiment(exp, vals['website_id'])
        return super(Experiment, self).create(vals)

    @api.multi
    def write(self, vals):
        state = vals.get('state')
        for exp in self:
            if state and exp.state == 'ended':
                raise Warning(_("You cannot modify an ended experiment."))
            elif state == 'ended':
                #google_data is the data to send to Googe
                google_data = {
                    'name': exp.name,
                    'status': state,
                    'variations': [{'name': 'master', 'url': 'http://localhost/master'}],
                }
                for exp_v in exp.experiment_version_ids:
                    google_data['variations'].append({'name': exp_v.version_id.name, 'url': 'http://localhost/'+exp_v.version_id.name})
                #to check the constraints before to write on the google analytics account
                self.env['google.management'].update_an_experiment(google_data, exp.google_id, exp.website_id.id)
        return super(Experiment, self).write(vals)

    @api.multi
    def unlink(self):
        for exp in self:
            self.env['google.management'].delete_an_experiment(exp.google_id, exp.website_id.id)
        return super(Experiment, self).unlink()

    def update_goals(self):
        gm_obj = self.env['google.management']
        goals_obj = self.env['website_version.goals']
        website_id = self.env.context.get('website_id')
        if not website_id:
            raise Warning("You must specify the website.")
        for goal in gm_obj.get_goal_info(website_id)[1]['items']:
            if not goals_obj.search([('name', '=', goal['name'])]):
                vals = {'name': goal['name'], 'google_ref': 'ga:goal' + goal['id'] + 'Completions'}
                goals_obj.create(vals)

    def check_no_overlap(self, version_ids):
        if self.search_count(['|', ('state', '=', 'running'), ('state', '=', 'paused')]) >= 24:
            return {'existing': TOO_MUCH_EXPERIMENTS, 'name': ""}
        #Check if version_ids don't overlap with running experiments and return the name of the experiment if there 's an overlap
        version_keys = set([v['key'] for v in self.env['ir.ui.view'].search_read([('version_id', 'in', version_ids)], ['key'])])
        exp_mod = self.env['website_version.experiment']
        exps = exp_mod.search([('state', '=', 'running'), ('website_id', '=', self.env.context.get('website_id'))])
        for exp in exps:
            for exp_ver in exp.experiment_version_ids:
                for view in exp_ver.version_id.view_ids:
                    if view.key in version_keys:
                        return {'existing': OVERLAP_EXPERIMENT, 'name': exp.name}
        return {'existing': CREATE_EXPERIMENT, 'name': ""}
