# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResUsers(models.Model):
    """
    Extend res.users to add warehouse-level access control

    Users can be assigned to multiple warehouses (Many2many).
    Users only see records related to their assigned warehouses.
    Warehouse Managers bypass all restrictions.
    """
    _inherit = 'res.users'

    # ====================
    # Fields
    # ====================

    warehouse_ids = fields.Many2many(
        'stock.warehouse',
        'camtel_user_warehouse_rel',
        'user_id',
        'warehouse_id',
        string='Allowed Warehouses',
        help="Warehouses this user can access. Leave empty and user sees nothing. "
             "Warehouse Managers see all warehouses regardless."
    )

    allowed_warehouse_ids = fields.Many2many(
        'stock.warehouse',
        compute='_compute_allowed_warehouse_ids',
        string='Computed Allowed Warehouses',
        help="Computed field for use in domain filters"
    )

    # ====================
    # Computed Fields
    # ====================

    @api.depends('warehouse_ids')
    @api.depends_context('uid')
    def _compute_allowed_warehouse_ids(self):
        """
        Compute warehouses user can access
        Managers get all warehouses automatically
        """
        for user in self:
            # Check if user is warehouse manager
            if user.has_group('camtel_core.group_warehouse_manager'):
                # Managers see all warehouses
                user.allowed_warehouse_ids = self.env['stock.warehouse'].search([])
            else:
                # Regular users see only assigned warehouses
                user.allowed_warehouse_ids = user.warehouse_ids

    # ====================
    # Helper Methods
    # ====================

    def has_warehouse_access(self, warehouse):
        """
        Check if user has access to a specific warehouse

        :param warehouse: stock.warehouse record
        :return: True if user can access this warehouse
        """
        self.ensure_one()

        # Managers have access to all
        if self.has_group('camtel_core.group_warehouse_manager'):
            return True

        # Check if warehouse in user's allowed list
        return warehouse in self.warehouse_ids

    def get_warehouse_domain(self):
        """
        Get domain filter for user's allowed warehouses
        Useful for manual domain filtering

        :return: Domain list for warehouse filtering
        """
        self.ensure_one()

        # Managers see all
        if self.has_group('camtel_core.group_warehouse_manager'):
            return []

        # Users see only assigned warehouses
        if self.warehouse_ids:
            return [('id', 'in', self.warehouse_ids.ids)]

        # No assignment = no access
        return [('id', '=', False)]

    # ====================
    # CRUD Overrides
    # ====================

    def write(self, vals):
        """
        Override write to invalidate caches when warehouse assignments change.

        Critical: Odoo caches record rules and user context. When warehouse_ids
        or groups_id changes, we must clear these caches to ensure record rules
        re-evaluate with the new warehouse assignments and group memberships.
        """
        # Check if warehouse assignments or group membership is being modified
        warehouse_assignment_changed = 'warehouse_ids' in vals or 'groups_id' in vals

        # Perform the write
        result = super().write(vals)

        if warehouse_assignment_changed:
            # Clear all relevant caches for affected users
            self._invalidate_warehouse_caches()

        return result

    def _invalidate_warehouse_caches(self):
        """
        Invalidate all caches related to warehouse access.

        This ensures record rules re-evaluate immediately with new assignments
        instead of serving stale cached results.
        """
        # 1. Invalidate the computed field cache
        self.invalidate_recordset(['allowed_warehouse_ids'])

        # 2. Invalidate the entire cache for warehouse-related models
        # This forces record rules to re-evaluate for these users
        models_to_invalidate = [
            'stock.warehouse',
            'stock.location',
            'stock.picking',
            'stock.move',
            'stock.move.line',
            'stock.quant',
            'product.product',
            'product.template',
        ]

        for model_name in models_to_invalidate:
            try:
                # Invalidate cache for all records of this model
                self.env[model_name].invalidate_model()
            except KeyError:
                # Model might not be installed, skip
                pass

        # 3. Clear the registry-level cache (includes record rules)
        # This is the nuclear option but ensures complete cache refresh
        self.env.registry.clear_cache()

        # 4. Invalidate user recordset to ensure fresh user data
        self.invalidate_recordset(['warehouse_ids'])
