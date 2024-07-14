# -*- coding: utf-8 -*-

from . import controllers
from . import models


def _documents_project_post_init(env):
    env['project.project'].search([('use_documents', '=', True)])._create_missing_folders()
