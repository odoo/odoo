import logging

from odoo import api, fields, models
from odoo.db.schema import column_exists
from odoo.tools import SQL, ormcache

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
    active = fields.Boolean(
        default=True,
        readonly=True,
        help="Archived when the operation is no longer declared by an installed "
        "model. The row keeps its enforcement, so declaring the operation again "
        "resumes it as it was.",
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
        zero.
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
        # upgrade is what creates the table and its newest column: without the
        # guard a database whose approval predates them does not boot at all, not
        # even to be upgraded.
        if column_exists(self.env.cr, self._table, "active"):
            self._sync_declared_gates()

    @api.model
    def _sync_declared_gates(self) -> None:
        """Make the rows agree with what the registry declares.

        A gate row is a place to put a decision, not a fact about the code, so a
        row whose operation the installed code no longer declares is archived
        rather than kept as a switch that governs nothing. It is archived with its
        decision, because the registry that finds a row stale may simply be one
        that did not load the code declaring it: a server started once on a
        shorter addons path must not turn an enforcing gate back into a watching
        one.
        """
        declared = self._get_declared_operations()
        gates = self.sudo().with_context(active_test=False).search([])
        existing = {(gate.model_name, gate.operation): gate for gate in gates}

        if stale := gates.filtered(
            lambda gate: (
                gate.active and (gate.model_name, gate.operation) not in declared
            )
        ):
            self._archive_undeclared_gates(stale)

        if revived := gates.filtered(
            lambda gate: (
                not gate.active and (gate.model_name, gate.operation) in declared
            )
        ):
            revived.active = True
            trace.REGISTRY.note(
                "gate_rows_restored",
                gates=[f"{gate.model_name}.{gate.operation}" for gate in revived],
            )
            if enforcing := revived.filtered("enforced"):
                _logger.info(
                    "Code gates declared again resume enforcing: %s",
                    ", ".join(f"{g.model_name}.{g.operation}" for g in enforcing),
                )

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
    def _archive_undeclared_gates(self, stale) -> None:
        if unloaded := self._get_modules_installed_not_loaded():
            _logger.warning(
                "Installed modules were not loaded (%s): the code gates %s are not "
                "declared by this registry and are left as they are.",
                ", ".join(sorted(unloaded)),
                ", ".join(f"{g.model_name}.{g.operation}" for g in stale),
            )
            return
        absent = {
            gate.model_name
            for gate in stale
            if gate.model_name not in self.env.registry
        }
        installed = self._get_models_of_installed_modules(absent)
        stale = stale.filtered(lambda gate: gate.model_name not in installed)
        if not stale:
            return
        trace.REGISTRY.note(
            "gate_rows_archived",
            gates=[f"{gate.model_name}.{gate.operation}" for gate in stale],
        )
        for gate in stale.filtered("enforced"):
            _logger.warning(
                "Code gate %s.%s was enforcing and is archived: %s. It resumes "
                "enforcing if the operation is declared again.",
                gate.model_name,
                gate.operation,
                "its model is not installed"
                if gate.model_name in absent
                else "its model no longer declares it",
            )
        stale.active = False

    @api.model
    def _get_modules_installed_not_loaded(self) -> set[str]:
        modules = (
            self.env["ir.module.module"]
            .sudo()
            .search_fetch([("state", "in", ("installed", "to upgrade"))], ["name"])
        )
        return set(modules.mapped("name")) - self.env.registry.loaded_modules

    @api.model
    def _get_models_of_installed_modules(self, model_names: set[str]) -> set[str]:
        if not model_names:
            return set()
        rows = self.env.execute_query(
            SQL(
                """
                SELECT DISTINCT model.model
                  FROM ir_model model
                  JOIN ir_model_data data
                    ON data.model = 'ir.model' AND data.res_id = model.id
                  JOIN ir_module_module module
                    ON module.name = data.module
                 WHERE model.model = ANY(%s)
                   AND module.state IN ('installed', 'to upgrade')
                """,
                sorted(model_names),
            )
        )
        return {model_name for (model_name,) in rows}

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
