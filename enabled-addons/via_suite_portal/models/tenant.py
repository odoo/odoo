# -*- coding: utf-8 -*-
import logging
import os
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.service import db as db_service

_logger = logging.getLogger(__name__)

class ViaSuiteTenant(models.Model):
    _name = 'via_suite.tenant'
    _description = 'ViaSuite Tenant'
    _order = 'name'

    name = fields.Char(string='Tenant Name', required=True)
    subdomain = fields.Char(string='Subdomain', required=True, help="Short name used in the URL: [subdomain].viafronteira.app")
    active = fields.Boolean(default=True)
    description = fields.Text()
    
    _sql_subdomain_unique = models.Constraint(
        'UNIQUE(subdomain)',
        'The subdomain must be unique!'
    )

    @api.depends('subdomain')
    def _compute_full_url(self):
        base_domain = os.getenv('VIA_SUITE_GLOBAL_DOMAIN', 'viafronteira.app')
        for tenant in self:
            tenant.full_url = f"https://{tenant.subdomain}.{base_domain}" if tenant.subdomain else ""

    @api.depends('subdomain')
    def _compute_db_name(self):
        for tenant in self:
            tenant.db_name = f"via-suite-{tenant.subdomain}" if tenant.subdomain else ""

    full_url = fields.Char(string='Full URL', compute='_compute_full_url')
    db_name = fields.Char(string='Database Name', compute='_compute_db_name', store=True)

    def _db_orchestration(self, func, *args, **kwargs):
        """
        Wrapper to execute database service functions bypassing the 'list_db' check.
        In production, 'list_db' is often False, which blocks these functions via a decorator.
        """
        import odoo.tools
        old_list_db = odoo.tools.config['list_db']
        try:
            odoo.tools.config['list_db'] = True
            return func(*args, **kwargs)
        finally:
            odoo.tools.config['list_db'] = old_list_db

    def _get_template_db(self):
        """ Get the template database from system parameters or default. """
        return self.env['ir.config_parameter'].sudo().get_param('via_suite.template_database', 'via-suite-template')

    @api.model_create_multi
    def create(self, vals_list):
        """
        Create Tenant record and physically clone the Odoo database.
        """
        tenants = super(ViaSuiteTenant, self).create(vals_list)
        template_db = self._get_template_db()

        for tenant in tenants:
            _logger.info("Orchestration: Creating database '%s' from template '%s'", tenant.db_name, template_db)
            try:
                # exp_duplicate_database(source, target)
                # Note: This requires the Odoo process to have correct PG permissions.
                # We wrap with _db_orchestration to bypass the 'list_db' check in production.
                self._db_orchestration(db_service.exp_duplicate_database, template_db, tenant.db_name)
            except Exception as e:
                _logger.error("Failed to create database for tenant %s: %s", tenant.subdomain, str(e))
                raise UserError(_("Could not create database '%s'. Please check PostgreSQL permissions or if the template '%s' exists.\nError: %s") % (tenant.db_name, template_db, str(e)))
        
        return tenants

    def write(self, vals):
        """
        Update Tenant record and synchronize physical database (Rename if subdomain changes).
        """
        if 'subdomain' in vals:
            for tenant in self:
                old_db = tenant.db_name
                new_db = f"via-suite-{vals['subdomain']}"
                if old_db != new_db:
                    _logger.info("Orchestration: Renaming database from '%s' to '%s'", old_db, new_db)
                    try:
                        self._db_orchestration(db_service.exp_rename, old_db, new_db)
                    except Exception as e:
                        _logger.error("Failed to rename database %s to %s: %s", old_db, new_db, str(e))
                        raise UserError(_("Could not rename database. Error: %s") % str(e))
        
        return super(ViaSuiteTenant, self).write(vals)

    def unlink(self):
        """
        Delete Tenant record and physically DROP the database.
        """
        for tenant in self:
            db_to_drop = tenant.db_name
            _logger.warning("Orchestration: DROPPING database '%s' physically!", db_to_drop)
            try:
                self._db_orchestration(db_service.exp_drop, db_to_drop)
            except Exception as e:
                _logger.error("Failed to drop database %s: %s", db_to_drop, str(e))
                # We don't necessarily block the unlink of the record, 
                # but it's safer to alert the user.
                raise UserError(_("Could not drop database '%s'. You may need to delete it manually.\nError: %s") % (db_to_drop, str(e)))
        
        return super(ViaSuiteTenant, self).unlink()

    def action_go_to_tenant(self):
        self.ensure_one()
        if not self.active:
            raise UserError(_("This tenant is inactive. Please activate it before accessing."))
        return {
            'type': 'ir.actions.act_url',
            'url': self.full_url,
            'target': 'new',
        }
