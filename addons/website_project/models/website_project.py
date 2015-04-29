# -*- coding: utf-8 -*-
from openerp import models


class Project(models.Model):
    _name = 'project.project'
    _inherit = ['project.project', 'website.seo.metadata']


class Task(models.Model):
    _name = 'project.task'
    _inherit = ['project.task', 'website.seo.metadata']
