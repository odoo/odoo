# Part of TNPD Prison Management System.
# License: LGPL-3

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class PrisonJail(models.Model):
    """
    Tamil Nadu prison hierarchy master (3 tiers).

    Hierarchy rules enforced by ``_check_hierarchy_integrity``:
        Central Jail  — no parent allowed
        District Jail — parent optional; if set, must be a Central Jail
                        (D.J. Nagapattinam / Pudukkottai are standalone)
        Sub Jail      — parent required; must be a Central Jail or District Jail
                        (Sub Jails without a District Jail are parented directly
                        to their administering Central Prison)

    ``_parent_store = True`` enables efficient subtree queries via
    ``parent_path``.  ``central_jail_id`` (stored computed) allows a
    single-field filter across all three levels.
    """

    _name = 'prison.jail'
    _description = 'Prison / Jail'
    _rec_name = 'name'
    _order = 'sequence, jail_type, name'
    _parent_name = 'parent_id'
    _parent_store = True

    JAIL_TYPE = [
        ('central_jail', 'Central Jail'),
        ('district_jail', 'District Jail'),
        ('sub_jail', 'Sub Jail'),
    ]

    # ── Core identity ─────────────────────────────────────────────────────────

    name = fields.Char(
        string='Jail Name',
        required=True,
        index=True,
    )
    code = fields.Char(
        string='Jail Code',
        index=True,
        copy=False,
        help='Short unique identifier for this jail (e.g. CP-CHN, DJ-CBE, SJ-POL).',
    )
    jail_type = fields.Selection(
        selection=JAIL_TYPE,
        string='Jail Type',
        required=True,
        index=True,
    )

    # ── Hierarchy ─────────────────────────────────────────────────────────────

    parent_id = fields.Many2one(
        comodel_name='prison.jail',
        string='Parent Jail',
        index=True,
        ondelete='restrict',
    )
    # Required by _parent_store; Odoo maintains this automatically.
    parent_path = fields.Char(index=True)
    child_ids = fields.One2many(
        comodel_name='prison.jail',
        inverse_name='parent_id',
        string='Child Jails',
    )
    child_count = fields.Integer(
        string='Sub-units',
        compute='_compute_child_count',
    )
    # Stored so that any model can filter "all employees under Central Jail X"
    # with a simple domain: [('x_central_jail_id', '=', central_id)]
    central_jail_id = fields.Many2one(
        comodel_name='prison.jail',
        string='Central Jail',
        compute='_compute_central_jail_id',
        store=True,
        index=True,
    )

    # ── Location ──────────────────────────────────────────────────────────────

    district = fields.Char(string='District', index=True)
    state_id = fields.Many2one(
        comodel_name='res.country.state',
        string='State',
        domain=[('country_id.code', '=', 'IN')],
    )

    # ── Administration ────────────────────────────────────────────────────────

    active = fields.Boolean(default=True)
    sequence = fields.Integer(
        default=10,
        help='Lower sequence numbers appear first in lists.',
    )
    external_ref = fields.Char(
        string='External Reference',
        index=True,
        copy=False,
        help='Reference ID used in legacy or external systems (e.g. PRIMS jail ID).',
    )
    notes = fields.Text(string='Notes')

    # ── SQL uniqueness constraints ────────────────────────────────────────────

    _uniq_code = models.Constraint(
        'UNIQUE (code)',
        'Jail code must be unique. Choose a different code.',
    )
    _uniq_name_type = models.Constraint(
        'UNIQUE (name, jail_type)',
        'A jail with this name already exists for the selected type.',
    )

    # ── Computed ──────────────────────────────────────────────────────────────

    def _compute_child_count(self):
        for rec in self:
            rec.child_count = self.env['prison.jail'].search_count(
                [('parent_id', '=', rec.id), ('active', '=', True)]
            )

    @api.depends('jail_type', 'parent_id', 'parent_id.jail_type', 'parent_id.parent_id')
    def _compute_central_jail_id(self):
        for rec in self:
            if rec.jail_type == 'central_jail':
                rec.central_jail_id = rec
            elif rec.jail_type == 'district_jail':
                # Standalone D.J.s (no parent) have no central jail
                rec.central_jail_id = rec.parent_id or False
            else:
                # sub_jail: parent may be a Central Jail (direct) or District Jail
                if not rec.parent_id:
                    rec.central_jail_id = False
                elif rec.parent_id.jail_type == 'central_jail':
                    rec.central_jail_id = rec.parent_id
                else:
                    rec.central_jail_id = rec.parent_id.parent_id or False

    # ── Constraints ───────────────────────────────────────────────────────────

    @api.constrains('jail_type', 'parent_id')
    def _check_hierarchy_integrity(self):
        type_labels = dict(self.JAIL_TYPE)
        for rec in self:
            if rec.jail_type == 'central_jail':
                if rec.parent_id:
                    raise ValidationError(
                        f'Central Jail "{rec.name}" cannot have a parent jail. '
                        'Remove the parent before saving.'
                    )

            elif rec.jail_type == 'district_jail':
                # Parent is optional (some D.J.s are standalone).
                if rec.parent_id and rec.parent_id.jail_type != 'central_jail':
                    raise ValidationError(
                        f'The parent of District Jail "{rec.name}" must be a Central Jail, '
                        f'but "{rec.parent_id.name}" is a '
                        f'{type_labels.get(rec.parent_id.jail_type, "unknown")}.'
                    )

            elif rec.jail_type == 'sub_jail':
                if not rec.parent_id:
                    raise ValidationError(
                        f'Sub Jail "{rec.name}" must be linked to a Central Jail or '
                        'District Jail via the Parent Jail field.'
                    )
                if rec.parent_id.jail_type not in ('central_jail', 'district_jail'):
                    raise ValidationError(
                        f'The parent of Sub Jail "{rec.name}" must be a Central Jail or '
                        f'District Jail, but "{rec.parent_id.name}" is a '
                        f'{type_labels.get(rec.parent_id.jail_type, "unknown")}.'
                    )

    # ── Onchange ──────────────────────────────────────────────────────────────

    @api.onchange('jail_type')
    def _onchange_jail_type(self):
        """Reset parent when type changes; return a type-appropriate domain."""
        self.parent_id = False
        return {'domain': {'parent_id': self._parent_type_domain()}}

    @api.onchange('parent_id')
    def _onchange_parent_id(self):
        """Inherit district / state from parent when not already set."""
        if not self.parent_id:
            return
        if not self.district:
            self.district = self.parent_id.district
        if not self.state_id:
            self.state_id = self.parent_id.state_id

    def _parent_type_domain(self):
        """Return the correct domain to restrict parent_id choices by jail_type."""
        if self.jail_type == 'district_jail':
            return [('jail_type', '=', 'central_jail'), ('active', '=', True)]
        if self.jail_type == 'sub_jail':
            # Sub Jails may be under a District Jail or directly under a Central Jail
            return [('jail_type', 'in', ['central_jail', 'district_jail']), ('active', '=', True)]
        return [('id', '=', False)]  # central jails have no valid parent

    # ── Name search ───────────────────────────────────────────────────────────

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=100, order=None):
        """Allow searching by either name or code in Many2one dropdowns."""
        domain = domain or []
        if name:
            domain = ['|', ('name', operator, name), ('code', operator, name)] + domain
        return self._search(domain, limit=limit, order=order)
