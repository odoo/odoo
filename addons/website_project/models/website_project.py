from openerp.osv import orm

class project(orm.Model):
    _name = 'project.project'
    _inherit = ['project.project','website.seo.metadata']

class task(orm.Model):
    _name = 'project.task'
    _inherit = ['project.task','website.seo.metadata']