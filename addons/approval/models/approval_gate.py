import logging

from odoo import api, fields, models
from odoo.db.schema import table_exists
from odoo.tools import ormcache

from . import approval_trace as trace

_logger = logging.getLogger(__name__)

LEGACY_ENFORCE_PARAM = "approval.gate_enforced"


class ApprovalGate(models.Model):
    """One row per terminal transition a model gates in its own code.

    The configured twin of `approval.binding`. A binding is created by a person
    who decided to gate a method; a gate is declared by the model itself, in
    `_approval_operations`, so nobody creates these -- the registry does. What is
    left for a person to decide is the only field they may write: whether the
    gate is enforcing yet, which is the decision the observation counts beside it
    exist to inform.
    """

    _name = "approval.gate"
    _description = "Approval Gate Declared In Code"
    _order = "model_name, operation"

    model_name = fields.Char(
        string="Model",
        index=True,
        readonly=True,
        required=True,
    )
    operation = fields.Char(
        index=True,
        readonly=True,
        required=True,
        help="The method the model declares as a terminal transition.",
    )
    model_id = fields.Many2one(
        comodel_name="ir.model",
        string="Model Record",
        compute="_compute_model_id",
    )
    enforced = fields.Boolean(
        help="While off, a call that reaches this operation by a path the gate "
        "does not own is recorded and let through. Switch it on once the watched "
        "calls show what refusing them would cost.",
    )
    would_block_count = fields.Integer(
        string="Would Be Refused",
        compute="_compute_would_block_count",
    )

    _model_operation_uniq = models.Constraint(
        "UNIQUE (model_name, operation)",
        "A model's operation is gated once.",
    )

    @api.depends("model_name")
    def _compute_model_id(self) -> None:
        for gate in self:
            gate.model_id = self.env["ir.model"]._get(gate.model_name)

    @api.depends("model_name", "operation")
    def _compute_would_block_count(self) -> None:
        """How many calls enforcing this gate would have refused.

        The only number the decision needs, and the only one a code gate can
        honestly offer: it records a call it would have refused and no other, so
        a second "how many arrived at all" column would repeat this one.
        """
        counts = {}
        for model_name, operation, count in self.env[
            "approval.observation"
        ]._read_group(
            [
                ("model_name", "in", self.mapped("model_name")),
                ("operation", "in", self.mapped("operation")),
                ("would_block", "=", True),
            ],
            ["model_name", "operation"],
            ["__count"],
        ):
            counts[(model_name, operation)] = count
        for gate in self:
            gate.would_block_count = counts.get((gate.model_name, gate.operation), 0)

    @api.model
    def _get_declared_operations(self) -> set[tuple[str, str]]:
        """The gated operations a row can actually govern.

        An operation earns a row only where the model also names a checkpoint for
        it. `_check_approval_admits` is called from that checkpoint and nowhere
        else, so without one there is no path for enforcement to close: the
        toggle would govern nothing and the count beside it could never leave
        zero. `mixin.approval.lifecycle` is the standing case -- it declares
        `action_confirm` for every order-like document and names no checkpoint.
        """
        declared = set()
        unenforceable = set()
        for model_name, Model in self.env.registry.items():
            if Model._abstract or Model._transient:
                continue
            checkpoints = getattr(Model, "_operation_checkpoints", {})
            for operation in getattr(Model, "_approval_operations", ()):
                target = declared if operation in checkpoints else unenforceable
                target.add((model_name, operation))
        if unenforceable:
            trace.REGISTRY.note(
                "gate_declared_without_checkpoint",
                operations=sorted(
                    f"{model_name}.{operation}"
                    for model_name, operation in unenforceable
                ),
            )
        return declared

    def _register_hook(self):
        super()._register_hook()
        # Every registry load reaches this, upgraded or not, and this module's own
        # upgrade is what creates the table: without the guard a database whose
        # approval predates the gate does not boot at all, not even to be upgraded.
        if table_exists(self.env.cr, self._table):
            self._sync_declared_gates()

    @api.model
    def _sync_declared_gates(self) -> None:
        """Make the rows agree with what the registry declares.

        A gate row is a place to put a decision, not a fact about the code, so a
        row whose operation the model no longer declares is deleted rather than
        kept as a switch that governs nothing. The decision is only lost when the
        code that needed it is gone.
        """
        declared = self._get_declared_operations()
        existing = {}
        for gate in self.sudo().search([]):
            existing[(gate.model_name, gate.operation)] = gate

        if stale := [gate for key, gate in existing.items() if key not in declared]:
            trace.REGISTRY.note(
                "gate_rows_dropped",
                gates=[f"{gate.model_name}.{gate.operation}" for gate in stale],
            )
            self.sudo().browse([gate.id for gate in stale]).unlink()

        if missing := sorted(declared - existing.keys()):
            self.sudo().create(
                [
                    {"model_name": model_name, "operation": operation}
                    for model_name, operation in missing
                ]
            )
            trace.REGISTRY.note(
                "gate_rows_created",
                gates=[
                    f"{model_name}.{operation}" for model_name, operation in missing
                ],
            )
        self._adopt_legacy_enforcement()

    @api.model
    def _adopt_legacy_enforcement(self) -> None:
        """Carry 19.0.2.9.0's single `approval.gate_enforced` onto the rows.

        It cannot be done in a migration: no migration phase runs late enough to
        see the rows, because every adopter has to be in the registry before the
        gates can be discovered and that only happens at `_register_hook`, after
        the end migrations. A database that was enforcing keeps enforcing --
        dropping it silently would turn enforcement off for whoever had switched
        it on.
        """
        parameters = self.env["ir.config_parameter"].sudo()
        legacy = parameters.search([("key", "=", LEGACY_ENFORCE_PARAM)])
        if not legacy:
            return
        if legacy.value == "1":
            gates = self.sudo().search([])
            gates.enforced = True
            _logger.info(
                "%s was set; every code gate is enforcing (%s). Enforcement is "
                "per operation now, under Approvals > Code Gates.",
                LEGACY_ENFORCE_PARAM,
                ", ".join(f"{g.model_name}.{g.operation}" for g in gates),
            )
        legacy.unlink()

    @api.model
    def _is_enforced(self, records, operation: str) -> bool:
        return (records._name, operation) in self._get_enforced_operations()

    @api.model
    @ormcache()
    def _get_enforced_operations(self) -> frozenset[tuple[str, str]]:
        """Cached like the binding's own lookup: a checkpoint asks on every call."""
        return frozenset(
            (gate.model_name, gate.operation)
            for gate in self.sudo().search([("enforced", "=", True)])
        )

    @api.model_create_multi
    def create(self, vals_list):
        gates = super().create(vals_list)
        self.env.registry.clear_cache()
        return gates

    def write(self, vals):
        result = super().write(vals)
        self.env.registry.clear_cache()
        return result

    def unlink(self):
        result = super().unlink()
        self.env.registry.clear_cache()
        return result

    def action_view_observations(self) -> dict:
        self.check_singleton()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Watched Calls"),
            "res_model": "approval.observation",
            "view_mode": "list",
            "domain": [
                ("model_name", "=", self.model_name),
                ("operation", "=", self.operation),
            ],
        }
