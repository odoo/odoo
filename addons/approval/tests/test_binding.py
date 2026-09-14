from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import common, tagged

from odoo.addons.approval.tests.common import add_category_approver


@tagged("post_install", "-at_install")
class TestApprovalBinding(common.TransactionCase):
    """Gating a method rather than waiting for a document to ask.

    The binding wraps the method at registry load, so the gate holds for every
    caller. These cover the wrapping itself, the three modes, and the two
    defects the incumbent implementation in `web_studio` has: an unconditional
    `sudo()` bypass, and patches that do not compose.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_model = cls.env["ir.model"]._get("res.partner")
        cls.Binding = cls.env["approval.binding"]
        cls.approver = cls.env["res.users"].create(
            {
                "name": "Binding Approver",
                "login": "binding_approver",
                "email": "binding_approver@test.com",
                "group_ids": [
                    (4, cls.env.ref("base.group_user").id),
                    (4, cls.env.ref("base.group_partner_manager").id),
                ],
            }
        )
        cls.category = cls.env["approval.category"].create(
            {
                "name": "Binding Category",
                "approval_minimum": 1,
                "allow_self_approval": True,
            }
        )
        add_category_approver(cls.category, cls.approver, required=True, sequence=10)

    def tearDown(self):
        for wrapper, real in reversed(getattr(self, "_swapped_origins", [])):
            wrapper.approval_binding_origin = real
        # the wrappers live on the registry, not in the transaction
        self.Binding._unregister_hook()
        super().tearDown()

    def _bind(self, **kwargs):
        vals = {
            "model_id": self.partner_model.id,
            "method": "action_archive",
            "mode": "advise",
        }
        vals.update(kwargs)
        binding = self.Binding.create(vals)
        self.Binding._unregister_hook()
        self.Binding._register_hook()
        return binding

    def _partner(self, **kwargs):
        vals = {"name": "Binding Partner"}
        vals.update(kwargs)
        return self.env["res.partner"].create(vals)

    # -- the wrapping itself ----------------------------------------------

    def test_registering_wraps_the_method_and_unregistering_restores_it(self):
        Partner = self.env.registry["res.partner"]
        self.assertFalse(hasattr(Partner.action_archive, "approval_binding_origin"))
        self._bind()
        Partner = self.env.registry["res.partner"]
        self.assertTrue(hasattr(Partner.action_archive, "approval_binding_origin"))
        self.Binding._unregister_hook()
        Partner = self.env.registry["res.partner"]
        self.assertFalse(hasattr(Partner.action_archive, "approval_binding_origin"))

    def test_two_bindings_on_one_method_share_a_single_wrapper(self):
        """Composition, not stacking: a second patch would make removal
        order-dependent, which is how `automation` loses other people's."""
        self._bind(subject_domain="[('is_company', '=', True)]")
        self._bind(subject_domain="[('is_company', '=', False)]")
        Partner = self.env.registry["res.partner"]
        wrapper = Partner.action_archive
        origin = wrapper.approval_binding_origin
        self.assertFalse(
            hasattr(origin, "approval_binding_origin"),
            "the wrapper wrapped another wrapper",
        )

    # -- observe mode ------------------------------------------------------

    def test_observe_mode_lets_the_call_through_and_records_it(self):
        binding = self._bind(mode="advise")
        partner = self._partner()
        partner.action_archive()
        self.assertFalse(partner.active, "observe mode must not block")
        self.assertEqual(binding.observation_count, 1)
        observation = binding.observation_ids
        self.assertEqual(observation.res_id, partner.id)
        self.assertTrue(observation.would_block)

    def test_observe_mode_separates_superuser_from_sudo_elevation(self):
        """The count that decides whether switching to Block is cheap."""
        binding = self._bind(mode="advise")
        self._partner().action_archive()
        self._partner().with_user(self.approver).sudo().action_archive()
        elevations = binding.observation_ids.mapped("elevation")
        self.assertIn("superuser", elevations)
        self.assertIn("self_elevated", elevations)
        self.assertEqual(binding.self_elevated_count, 1)

    def _plain_user(self):
        return self.env["res.users"].create(
            {
                "name": "Plain Caller",
                "login": "binding_plain",
                "email": "binding_plain@test.com",
                "group_ids": [
                    (4, self.env.ref("base.group_user").id),
                    (4, self.env.ref("base.group_partner_manager").id),
                ],
            }
        )

    def test_an_ordinary_caller_is_recorded_as_not_elevated(self):
        """Elevation is the caller's, not the binding's.

        The binding is read through `sudo()`. Measured on its own env, every
        caller looked elevated, so this row read `self_elevated` for a user who
        never called `sudo()` at all.
        """
        binding = self._bind(mode="advise")
        self._partner().with_user(self._plain_user()).action_archive()
        self.assertEqual(binding.observation_ids.elevation, "none")
        self.assertEqual(binding.self_elevated_count, 0)

    def test_the_bypass_policy_does_not_wave_an_ordinary_caller_through(self):
        """The defect that made the elevation bug a security bug.

        "Any elevated caller passes" is meant for callers that ARE elevated.
        With elevation measured on the sudo()ed binding, an ordinary user
        counted as elevated and passed a Block gate untouched.
        """
        self._bind(mode="block", category_id=self.category.id, sudo_policy="bypass")
        partner = self._partner()
        with self.assertRaises(UserError):
            partner.with_user(self._plain_user()).action_archive()
        self.assertTrue(partner.active, "the gate must not have been bypassed")

    def test_a_call_on_many_records_observes_each_of_them(self):
        binding = self._bind(mode="advise")
        partners = self._partner() | self._partner() | self._partner()
        partners.action_archive()
        self.assertEqual(binding.observation_count, 3)
        self.assertEqual(
            set(binding.observation_ids.mapped("res_id")), set(partners.ids)
        )

    def test_a_binding_only_fires_on_records_its_domain_selects(self):
        binding = self._bind(subject_domain="[('is_company', '=', True)]")
        self._partner(is_company=False).action_archive()
        self.assertEqual(binding.observation_count, 0)
        self._partner(is_company=True).action_archive()
        self.assertEqual(binding.observation_count, 1)

    # -- block mode --------------------------------------------------------

    def test_block_mode_refuses_an_unapproved_record(self):
        self._bind(mode="block", category_id=self.category.id, sudo_policy="enforce")
        partner = self._partner()
        with self.assertRaises(UserError):
            partner.action_archive()
        self.assertTrue(partner.active, "the operation must not have run")

    def test_block_mode_is_bypassed_by_the_superuser_under_the_default_policy(self):
        self._bind(mode="block", category_id=self.category.id)
        partner = self._partner()
        partner.action_archive()
        self.assertFalse(partner.active)

    def test_block_mode_does_not_let_an_ordinary_user_self_elevate(self):
        """`sudo()` keeps `uid`, so this is exactly what web_studio lets past."""
        self._bind(mode="block", category_id=self.category.id)
        partner = self._partner()
        with self.assertRaises(UserError):
            partner.with_user(self.approver).sudo().action_archive()
        self.assertTrue(partner.active)

    def test_the_kill_switch_disables_every_binding(self):
        self._bind(mode="block", category_id=self.category.id, sudo_policy="enforce")
        self.env["ir.config_parameter"].sudo().set_param(
            "approval.binding_enabled", "False"
        )
        partner = self._partner()
        partner.action_archive()
        self.assertFalse(partner.active)

    # -- configuration-time validation -------------------------------------

    def test_a_binding_on_a_method_automation_claims_is_refused(self):
        """`automation._unregister_hook` delattrs these registry-wide."""
        for method in ("create", "write", "unlink", "message_post"):
            with self.assertRaises(ValidationError):
                self.Binding.create(
                    {"model_id": self.partner_model.id, "method": method}
                )

    def test_a_binding_on_a_method_that_does_not_exist_is_refused(self):
        with self.assertRaises(ValidationError):
            self.Binding.create(
                {"model_id": self.partner_model.id, "method": "no_such_method"}
            )

    def test_a_binding_on_a_python_protocol_name_is_refused(self):
        """An Observe binding on `__setattr__` once broke building any partner."""
        for method in ("__setattr__", "__init__", "__getitem__"):
            with self.subTest(method=method), self.assertRaises(ValidationError):
                self.Binding.create(
                    {"model_id": self.partner_model.id, "method": method}
                )

    def test_a_binding_on_the_orm_api_is_refused(self):
        """The gate calls these itself, so wrapping one recurses or breaks the model."""
        for method in (
            "search",
            "browse",
            "sudo",
            "with_context",
            "filtered_domain",
            "check_access",
            "_unregister_hook",
        ):
            with self.subTest(method=method), self.assertRaises(ValidationError):
                self.Binding.create(
                    {"model_id": self.partner_model.id, "method": method}
                )

    def test_the_orm_lifecycle_actions_may_be_gated(self):
        for method in ("action_archive", "action_unarchive", "toggle_active"):
            with self.subTest(method=method):
                binding = self.Binding.create(
                    {"model_id": self.partner_model.id, "method": method}
                )
                self.assertTrue(binding.exists())

    def test_a_private_method_is_accepted_only_from_module_data(self):
        with self.assertRaises(ValidationError):
            self.Binding.create(
                {"model_id": self.partner_model.id, "method": "_fields_sync"}
            )
        binding = self.Binding.with_context(install_module="approval").create(
            {"model_id": self.partner_model.id, "method": "_fields_sync"}
        )
        binding.write({"subject_domain": "[('active', '=', True)]"})
        self.assertEqual(binding.subject_domain, "[('active', '=', True)]")

    def test_a_stored_binding_on_the_orm_api_is_not_applied(self):
        """A row written before the refusal existed must not wrap the method at load."""
        binding = self._bind()
        self.env.cr.execute(
            "UPDATE approval_binding SET method = 'with_context' WHERE id = %s",
            [binding.id],
        )
        binding.invalidate_recordset(["method"])
        self.env.registry.clear_cache()
        self.Binding._unregister_hook()
        with self.assertLogs("odoo.addons.approval.models.approval_binding", "WARNING"):
            self.Binding._register_hook()
        partner_class = self.env.registry["res.partner"]
        self.assertIsNone(
            getattr(partner_class.with_context, "approval_binding_origin", None)
        )
        self.assertTrue(self.env["res.partner"].create({"name": "Buildable"}).exists())

    def test_block_and_request_modes_need_a_category(self):
        with self.assertRaises(ValidationError):
            self.Binding.create(
                {
                    "model_id": self.partner_model.id,
                    "method": "action_archive",
                    "mode": "block",
                }
            )

    def test_request_mode_refuses_a_method_it_could_not_replay(self):
        """Storing arbitrary call arguments to replay later is where this
        design would start guessing, so the limit is enforced up front.

        `activity_feedback` also annotates with a name its module never imports,
        so reading its signature the default way raises NameError on 3.14.
        """
        with self.assertRaises(ValidationError):
            self.Binding.create(
                {
                    "model_id": self.partner_model.id,
                    "method": "activity_feedback",
                    "mode": "request",
                    "category_id": self.category.id,
                }
            )

    def test_a_domain_naming_an_unknown_field_is_refused(self):
        with self.assertRaises(ValidationError):
            self.Binding.create(
                {
                    "model_id": self.partner_model.id,
                    "method": "action_archive",
                    "subject_domain": "[('is_compayn', '=', True)]",
                }
            )

    def test_a_binding_cannot_gate_the_binding_machinery(self):
        with self.assertRaises(ValidationError):
            self.Binding.create(
                {
                    "model_id": self.env["ir.model"]._get("approval.binding").id,
                    "method": "action_archive",
                }
            )

    # -- request mode ------------------------------------------------------

    def _user(self, login, *groups):
        return self.env["res.users"].create(
            {
                "name": login,
                "login": login,
                "email": f"{login}@test.com",
                "group_ids": [
                    (4, self.env.ref(xmlid).id)
                    for xmlid in ("base.group_user", *groups)
                ],
            }
        )

    def _request_binding(self, **kwargs):
        return self._bind(mode="request", category_id=self.category.id, **kwargs)

    def _requests_for(self, binding, partner):
        return self.env["approval.request"].search(
            [
                ("binding_id", "=", binding.id),
                ("res_model", "=", "res.partner"),
                ("res_id", "=", partner.id),
            ]
        )

    def _approve(self, request):
        request.approver_ids.filtered(lambda a: a.user_id == self.approver).with_user(
            self.approver
        ).action_approve()

    def _refuse(self, request, user=None):
        user = user or self.approver
        request.approver_ids.filtered(lambda a: a.user_id == user).with_user(
            user
        ).with_context(skip_wizard=True).action_refuse()

    def _two_step_binding(self, peer, later):
        category = self.env["approval.category"].create(
            {"name": "Two Steps", "approval_minimum": 1}
        )
        for sequence, users in ((10, (self.approver, peer)), (20, (later,))):
            self.env["approval.category.step"].create(
                {
                    "category_id": category.id,
                    "name": f"Step {sequence}",
                    "sequence": sequence,
                    "member_ids": [(0, 0, {"user_id": user.id}) for user in users],
                }
            )
        return self._bind(
            mode="request", category_id=category.id, run_on_approval=False
        )

    def test_request_mode_asks_for_approval_instead_of_running(self):
        binding = self._request_binding()
        requester = self._user("binding_req_a", "base.group_partner_manager")
        partner = self._partner()
        action = partner.with_user(requester).action_archive()
        self.assertTrue(partner.active, "the operation must not have run yet")
        request = self._requests_for(binding, partner)
        self.assertEqual(len(request), 1)
        self.assertEqual(request.state, "pending")
        self.assertEqual(request.request_owner_id, requester)
        self.assertEqual(action["res_model"], "approval.request")

    def test_calling_again_while_pending_does_not_raise_a_second_request(self):
        binding = self._request_binding()
        requester = self._user("binding_req_b", "base.group_partner_manager")
        partner = self._partner()
        partner.with_user(requester).action_archive()
        partner.with_user(requester).action_archive()
        self.assertEqual(len(self._requests_for(binding, partner)), 1)

    def test_approval_runs_the_operation_once_as_the_requester(self):
        binding = self._request_binding()
        requester = self._user("binding_req_c", "base.group_partner_manager")
        partner = self._partner()
        partner.with_user(requester).action_archive()
        request = self._requests_for(binding, partner)
        self._approve(request)
        self.assertFalse(partner.active, "approval must run the operation")
        self.assertEqual(partner.write_uid, requester, "as the requester")
        self.assertTrue(request.date_binding_replayed)
        self.assertFalse(request.binding_replay_error)

    def test_a_second_approval_after_a_withdrawal_does_not_run_it_again(self):
        binding = self._request_binding()
        requester = self._user("binding_req_d", "base.group_partner_manager")
        partner = self._partner()
        partner.with_user(requester).action_archive()
        request = self._requests_for(binding, partner)
        self._approve(request)
        replayed = request.date_binding_replayed
        partner.action_unarchive()
        request.with_user(self.approver).action_withdraw()
        self._approve(request)
        self.assertTrue(partner.active, "a second approval must not replay")
        self.assertEqual(request.date_binding_replayed, replayed)

    def test_an_approval_does_not_lend_the_approver_their_rights(self):
        """The requester could not archive; the approver could.

        Replaying as the approver would archive the partner with rights the
        requester never had. It must not run, and the decision must stand.
        """
        binding = self._request_binding()
        requester = self._user("binding_req_e")
        partner = self._partner()
        partner.with_user(requester).action_archive()
        request = self._requests_for(binding, partner)
        self._approve(request)
        self.assertTrue(partner.active, "it ran with somebody else's rights")
        self.assertEqual(request.state, "approved", "the decision itself stands")
        self.assertTrue(request.binding_replay_error)
        self.assertFalse(request.date_binding_replayed)

    def test_a_record_changed_since_the_request_is_not_run(self):
        binding = self._request_binding(subject_domain="[('city', '!=', 'Nowhere')]")
        requester = self._user("binding_req_f", "base.group_partner_manager")
        partner = self._partner(city="Before")
        partner.with_user(requester).action_archive()
        request = self._requests_for(binding, partner)
        self.assertEqual(request.binding_snapshot, {"city": ["Before"]})
        partner.city = "After"
        self._approve(request)
        self.assertTrue(partner.active, "approved values moved, so it must not run")
        self.assertEqual(request.state, "approved")
        self.assertTrue(request.binding_replay_error)
        self.assertEqual(
            len(self._requests_for(binding, partner)),
            1,
            "and the replay must not raise another request",
        )

    def test_block_mode_passes_once_an_approved_request_points_at_the_record(self):
        self._bind(mode="block", category_id=self.category.id, sudo_policy="enforce")
        partner = self._partner()
        request = self.env["approval.request"].create(
            {
                "name": "Approved separately",
                "category_id": self.category.id,
                "request_owner_id": self.env.user.id,
                "res_model": "res.partner",
                "res_id": partner.id,
            }
        )
        request.action_confirm()
        self._approve(request)
        partner.action_archive()
        self.assertFalse(partner.active)

    # -- approve on invoke, run on approval ----------------------------------

    # -- a refusal stands ----------------------------------------------------

    def test_a_refusal_stands_and_the_next_call_raises_no_new_request(self):
        binding = self._request_binding()
        requester = self._user("binding_ref_a", "base.group_partner_manager")
        partner = self._partner()
        partner.with_user(requester).action_archive()
        request = self._requests_for(binding, partner)
        self._refuse(request)
        action = partner.with_user(requester).action_archive()
        self.assertTrue(partner.active)
        self.assertEqual(self._requests_for(binding, partner), request)
        self.assertEqual(action["res_id"], request.id, "the refusal is what is shown")

    def test_the_refuser_does_not_pass_by_invoking_again(self):
        """Studio's test_04: a manager cannot proceed past their own rejection."""
        binding = self._request_binding(approve_on_invoke=True, run_on_approval=False)
        requester = self._user("binding_ref_b", "base.group_partner_manager")
        partner = self._partner()
        partner.with_user(requester).action_archive()
        request = self._requests_for(binding, partner)
        self._refuse(request)
        partner.with_user(self.approver).action_archive()
        self.assertTrue(partner.active, "approve on invoke must not undo a refusal")
        self.assertEqual(request.state, "refused")
        self.assertEqual(len(self._requests_for(binding, partner)), 1)

    def test_the_requester_cannot_reopen_a_refusal(self):
        binding = self._request_binding()
        requester = self._user("binding_ref_c", "base.group_partner_manager")
        partner = self._partner()
        partner.with_user(requester).action_archive()
        request = self._requests_for(binding, partner)
        self._refuse(request)
        with self.assertRaises(AccessError):
            request.with_user(requester).action_reset_to_draft()

    def test_the_refuser_reopens_and_the_next_call_asks_again(self):
        binding = self._request_binding()
        requester = self._user("binding_ref_d", "base.group_partner_manager")
        partner = self._partner()
        partner.with_user(requester).action_archive()
        request = self._requests_for(binding, partner)
        self._refuse(request)
        request.with_user(self.approver).action_reset_to_draft()
        self.assertEqual(request.state, "new")
        partner.with_user(requester).action_archive()
        self.assertEqual(self._requests_for(binding, partner), request)
        self.assertEqual(request.state, "pending")

    def test_a_later_step_member_may_reopen_a_refusal_and_a_peer_may_not(self):
        peer = self._user("binding_ref_peer", "base.group_partner_manager")
        later = self._user("binding_ref_later", "base.group_partner_manager")
        binding = self._two_step_binding(peer, later)
        requester = self._user("binding_ref_e", "base.group_partner_manager")
        partner = self._partner()
        partner.with_user(requester).action_archive()
        request = self._requests_for(binding, partner)
        self._refuse(request)
        with self.assertRaises(AccessError):
            request.with_user(peer).action_reset_to_draft()
        request.with_user(later).action_reset_to_draft()
        self.assertEqual(request.state, "new")

    # -- withdrawing across steps -------------------------------------------

    def test_a_later_step_member_may_withdraw_an_earlier_approval_and_a_peer_may_not(
        self,
    ):
        """Studio's test_can_revoke_approval_with_inferior_order."""
        peer = self._user("binding_wd_peer", "base.group_partner_manager")
        later = self._user("binding_wd_later", "base.group_partner_manager")
        binding = self._two_step_binding(peer, later)
        requester = self._user("binding_wd_a", "base.group_partner_manager")
        partner = self._partner()
        partner.with_user(requester).action_archive()
        request = self._requests_for(binding, partner)
        self._approve(request)
        row = request.approver_ids.filtered(lambda a: a.user_id == self.approver)
        self.assertEqual(row.state, "approved")
        with self.assertRaises(AccessError):
            request.with_user(peer).action_withdraw_approver(row.id)
        request.with_user(later).action_withdraw_approver(row.id)
        self.assertEqual(row.state, "pending")

    def test_an_approver_withdraws_their_own_approval_through_the_same_door(self):
        binding = self._request_binding(run_on_approval=False)
        requester = self._user("binding_wd_b", "base.group_partner_manager")
        partner = self._partner()
        partner.with_user(requester).action_archive()
        request = self._requests_for(binding, partner)
        self._approve(request)
        row = request.approver_ids.filtered(lambda a: a.user_id == self.approver)
        request.with_user(self.approver).action_withdraw_approver(row.id)
        self.assertEqual(row.state, "pending")

    def _count_runs(self):
        """Record every time the gated method's body actually runs.

        Archiving twice looks exactly like archiving once, so a double run is
        invisible to the record. The wrapper reads its origin at call time, so
        swapping that reference counts executions without touching the method.
        """
        wrapper = self.env.registry["res.partner"].action_archive
        real = wrapper.approval_binding_origin
        runs = []

        def counting(records, *args, **kwargs):
            runs.append(tuple(records.ids))
            return real(records, *args, **kwargs)

        wrapper.approval_binding_origin = counting
        self._swapped_origins = [
            *getattr(self, "_swapped_origins", []),
            (wrapper, real),
        ]
        return runs

    def test_an_invoking_approver_runs_the_operation_exactly_once(self):
        """Their click approves AND runs; the replay must not run it a second time."""
        binding = self._request_binding(approve_on_invoke=True)
        runs = self._count_runs()
        partner = self._partner()
        partner.with_user(self.approver).action_archive()
        self.assertEqual(runs, [(partner.id,)], "run once, by the call itself")
        self.assertFalse(partner.active)
        request = self._requests_for(binding, partner)
        self.assertEqual(request.state, "approved")
        self.assertTrue(request.date_binding_replayed, "the one-shot is stamped")

    def test_invoking_without_the_right_to_approve_only_raises_the_request(self):
        binding = self._request_binding(approve_on_invoke=True)
        requester = self._user("binding_inv_a", "base.group_partner_manager")
        runs = self._count_runs()
        partner = self._partner()
        partner.with_user(requester).action_archive()
        self.assertEqual(runs, [])
        self.assertEqual(self._requests_for(binding, partner).state, "pending")

    def test_invoke_records_only_the_steps_the_caller_may_decide(self):
        category = self.env["approval.category"].create(
            {"name": "Invoke Steps", "approval_minimum": 1}
        )
        second = self._user("binding_inv_c", "base.group_partner_manager")
        for sequence, user in ((10, self.approver), (20, second)):
            self.env["approval.category.step"].create(
                {
                    "category_id": category.id,
                    "name": f"Step {sequence}",
                    "sequence": sequence,
                    "member_ids": [(0, 0, {"user_id": user.id})],
                }
            )
        binding = self._bind(
            mode="request",
            category_id=category.id,
            approve_on_invoke=True,
            run_on_approval=False,
        )
        runs = self._count_runs()
        partner = self._partner()
        partner.with_user(self.approver).action_archive()
        request = self._requests_for(binding, partner)
        self.assertEqual(runs, [], "one step of two is not enough")
        self.assertEqual(request.state, "pending")
        request.with_user(second).action_approve()
        self.assertEqual(request.state, "approved")
        self.assertEqual(runs, [], "run on approval is off, so approval runs nothing")
        partner.with_user(self.approver).action_archive()
        self.assertEqual(runs, [(partner.id,)], "the next call is covered and runs")

    def test_run_on_approval_off_leaves_the_operation_to_the_next_call(self):
        binding = self._request_binding(run_on_approval=False)
        requester = self._user("binding_inv_b", "base.group_partner_manager")
        runs = self._count_runs()
        partner = self._partner()
        partner.with_user(requester).action_archive()
        self._approve(self._requests_for(binding, partner))
        self.assertEqual(runs, [])
        self.assertTrue(partner.active)
        partner.with_user(requester).action_archive()
        self.assertEqual(runs, [(partner.id,)])

    def test_approve_on_invoke_needs_request_mode(self):
        with self.assertRaises(ValidationError):
            self.Binding.create(
                {
                    "model_id": self.partner_model.id,
                    "method": "action_archive",
                    "mode": "block",
                    "category_id": self.category.id,
                    "approve_on_invoke": True,
                }
            )

    def test_without_run_on_approval_a_method_with_arguments_may_be_gated(self):
        """The zero-argument limit exists only because a replay has no arguments."""
        binding = self.Binding.create(
            {
                "model_id": self.partner_model.id,
                "method": "activity_feedback",
                "mode": "request",
                "category_id": self.category.id,
                "run_on_approval": False,
            }
        )
        self.assertTrue(binding.exists())
