"""Tests for client-split feature on KSW_commissions.

Covers:
  • KswSalespersonProfileClientSplit: creation, client_names computed
  • Split rule must have scope 'client' or 'employee_client'
  • Split line role/targets come from split definition (not profile)
  • General line targets come from salesperson profile
  • General + split lines for same employee on same sheet — allowed
  • Duplicate split lines (same split_id) on same sheet — rejected
  • Duplicate general lines (split_id=False) on same sheet — rejected
  • _get_profile_rule: split line → split.rule_id; kind mismatch → empty
  • _get_profile_rule: general line → profile explicit rule
  • Commission computed independently per line (split vs general)
  • General line achieved_sales set to full total never reduced by split
  • _resolve_rule: client-scope rule matched by partner
  • _resolve_rule: employee+client beats client-only for same partner
  • x_collection_based_on_total flag present on ksw.salesperson.profile
  • res.partner has x_client_account_number and x_commission_import_name
"""
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


def _tier(from_pct=0.0, to_pct=100.0, rate_pct=1.0, base='achieved'):
    """Default to achieved-base so tests work even when target_sales=0.

    Split lines always have target_sales=0 (set by _compute_role_and_targets);
    using base='achieved' means tier amount is proportional to achieved_sales
    regardless of target, matching real production split-rule configuration.
    """
    return {'from_pct': from_pct, 'to_pct': to_pct,
            'rate_pct': rate_pct, 'base': base}


class TestClientSplits(TransactionCase):
    """Tests covering client-split functionality across profiles and sheets."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env

        # ---- Employees -------------------------------------------------
        cls.emp = env['hr.employee'].sudo().create({
            'name': 'Split Test Employee', 'x_is_attendance_sheet': True,
        })
        cls.emp_b = env['hr.employee'].sudo().create({
            'name': 'Split Test Employee B', 'x_is_attendance_sheet': True,
        })

        # ---- Partners (clients) ----------------------------------------
        cls.partner_a = env['res.partner'].sudo().create({
            'name': 'Split Client Alfa', 'customer_rank': 1,
        })
        cls.partner_b = env['res.partner'].sudo().create({
            'name': 'Split Client Beta', 'customer_rank': 1,
        })
        cls.partner_c = env['res.partner'].sudo().create({
            'name': 'Split Client Gamma', 'customer_rank': 1,
        })

        # ---- Commission rules ------------------------------------------
        # General sales rule (scope=general) — applies to everyone
        cls.gen_sales_rule = cls._mk_rule(
            env, 'gen_sales', kind='sales', scope='general',
            tiers=[_tier(rate_pct=2.0)],
        )
        # General collection rule
        cls.gen_coll_rule = cls._mk_rule(
            env, 'gen_coll', kind='collection', scope='general',
            tiers=[_tier(rate_pct=3.0)],
        )
        # Client-specific sales rule — applies to partner_a + partner_b
        cls.client_sales_rule = cls._mk_rule(
            env, 'client_sales', kind='sales', scope='client',
            partners=[cls.partner_a, cls.partner_b],
            tiers=[_tier(rate_pct=1.0)],
        )
        # Employee + client rule for emp (higher specificity)
        cls.emp_client_rule = cls._mk_rule(
            env, 'emp_client', kind='sales', scope='employee_client',
            employee=cls.emp, partners=[cls.partner_a],
            tiers=[_tier(rate_pct=5.0)],
        )

        # ---- Salesperson profile (year 2099, far future to avoid clashes) --
        cls.profile = env['ksw.salesperson.profile'].sudo().create({
            'employee_id': cls.emp.id,
            'year': 2099,
            'role': 'both',
            'annual_sales_target': 120_000.0,
            'annual_collection_target': 60_000.0,
            'sales_rule_id': cls.gen_sales_rule.id,
            'collection_rule_id': cls.gen_coll_rule.id,
        })

        # ---- Client split on the profile --------------------------------
        cls.split = env['ksw.salesperson.profile.client.split'].sudo().create({
            'profile_id': cls.profile.id,
            'sequence': 10,
            'label': 'Special Clients Sales',
            'rule_id': cls.client_sales_rule.id,
            'role': 'sales',
        })

        cls.period = '2099-06-01'

    # ------------------------------------------------------------------
    # Class-level factory helpers
    # ------------------------------------------------------------------

    @classmethod
    def _mk_rule(cls, env, name_suffix, kind='sales', scope='general',
                 employee=None, partners=None,
                 condition_type='single_threshold',
                 sales_min=0.0, coll_min=0.0,
                 tiers=None, priority=10):
        vals = {
            'name': f'CSplit Rule {name_suffix}',
            'kind': kind, 'scope': scope,
            'condition_type': condition_type,
            'single_threshold_metric': 'collection' if kind == 'collection' else 'sales',
            'sales_min_pct': sales_min,
            'collection_min_pct': coll_min,
            'priority': priority,
        }
        if employee:
            vals['employee_id'] = employee.id
        # Include partner_ids in create so _check_scope_fields sees them.
        if partners:
            vals['partner_ids'] = [(4, p.id) for p in partners]
        r = env['ksw.sales.commission.rule'].sudo().create(vals)
        for t in (tiers or [_tier()]):
            env['ksw.sales.commission.tier'].sudo().create({'rule_id': r.id, **t})
        return r

    def _sc_sheet(self, period=None):
        return self.env['ksw.sales.commission.sheet'].sudo().create({
            'period': period or self.period,
        })

    def _sc_line(self, sheet, emp, achieved_sales=0.0, achieved_coll=0.0,
                 role=None, split_id=None, target_sales=None,
                 target_coll=None):
        vals = {
            'sheet_id': sheet.id,
            'employee_id': emp.id,
            'achieved_sales': achieved_sales,
            'achieved_collection': achieved_coll,
        }
        if role:
            vals['role'] = role
        if split_id:
            vals['split_id'] = split_id
        # For split lines: do NOT pass target_sales/target_coll in create vals.
        # Odoo ORM honours user-provided values for store=True/readonly=False
        # computed fields and skips the compute, leaving role=False.  For split
        # lines _compute_role_and_targets sets target_sales=0 anyway.
        if target_sales is not None and not split_id:
            vals['target_sales'] = target_sales
        if target_coll is not None and not split_id:
            vals['target_collection'] = target_coll
        line = self.env['ksw.sales.commission.line'].sudo().create(vals)
        # Invalidate the in-memory cache so subsequent field reads reflect
        # the DB-stored values (after all stored computes have settled).
        line.invalidate_recordset()
        return line

    # ==================================================================
    # 1. KswSalespersonProfileClientSplit model
    # ==================================================================

    def test_01_split_record_created(self):
        """A split record can be created on a profile."""
        self.assertTrue(self.split.id)
        self.assertEqual(self.split.profile_id, self.profile)
        self.assertEqual(self.split.label, 'Special Clients Sales')
        self.assertEqual(self.split.role, 'sales')

    def test_02_split_client_names_computed(self):
        """client_names shows partner names from the rule's partner_ids."""
        names = self.split.client_names
        self.assertIn('Split Client Alfa', names)
        self.assertIn('Split Client Beta', names)

    def test_03_split_client_names_updates_when_rule_changes(self):
        """client_names recomputes when rule_id changes."""
        # Create a rule with only partner_c
        rule2 = self._mk_rule(
            self.env, 'only_c', kind='sales', scope='client',
            partners=[self.partner_c], tiers=[_tier(rate_pct=1.0)],
        )
        split2 = self.env['ksw.salesperson.profile.client.split'].sudo().create({
            'profile_id': self.profile.id,
            'label': 'Temp Split', 'rule_id': rule2.id, 'role': 'sales',
        })
        self.assertIn('Split Client Gamma', split2.client_names)
        self.assertNotIn('Alfa', split2.client_names)
        # Clean up
        split2.sudo().unlink()

    def test_04_split_profile_has_split_ids(self):
        """Profile split_ids includes the created split."""
        self.assertIn(self.split, self.profile.split_ids)

    # ==================================================================
    # 2. Split line role & targets on commission sheet
    # ==================================================================

    def test_05_split_line_role_from_split(self):
        """Split line role = split_id.role (not profile role)."""
        # Profile role = 'both'; split role = 'sales'
        sheet = self._sc_sheet(period='2099-01-01')
        line = self._sc_line(sheet, self.emp, split_id=self.split.id)
        self.assertEqual(line.role, 'sales',
                         "Split line should inherit role from split, not profile")

    def test_06_split_line_targets_are_zero(self):
        """Split line target_sales and target_collection default to 0."""
        sheet = self._sc_sheet(period='2099-02-01')
        line = self._sc_line(sheet, self.emp, split_id=self.split.id)
        self.assertEqual(line.target_sales, 0.0)
        self.assertEqual(line.target_collection, 0.0)

    def test_07_general_line_uses_profile_targets(self):
        """General line (split_id=False) targets come from profile monthly row."""
        sheet = self._sc_sheet(period='2099-03-01')
        # General line
        line = self._sc_line(sheet, self.emp)
        # profile annual_sales_target=120000 → monthly = 10 000
        self.assertAlmostEqual(line.target_sales, 10_000.0, delta=1.0)
        # profile annual_collection_target=60000 → monthly = 5 000
        self.assertAlmostEqual(line.target_collection, 5_000.0, delta=1.0)

    # ==================================================================
    # 3. Uniqueness constraints
    # ==================================================================

    def test_08_general_and_split_lines_allowed_together(self):
        """One general + one split line for same employee → allowed."""
        sheet = self._sc_sheet(period='2099-04-01')
        general = self._sc_line(sheet, self.emp, achieved_sales=100_000.0)
        split_line = self._sc_line(sheet, self.emp, split_id=self.split.id,
                                   achieved_sales=40_000.0)
        self.assertTrue(general and split_line)

    def test_09_duplicate_general_line_rejected(self):
        """Two general lines (split=False) for same employee → ValidationError."""
        sheet = self._sc_sheet(period='2099-05-01')
        self._sc_line(sheet, self.emp, achieved_sales=50_000.0)
        with self.assertRaises(ValidationError):
            self._sc_line(sheet, self.emp, achieved_sales=60_000.0)

    def test_10_duplicate_split_line_rejected(self):
        """Two lines with the same split_id for same employee → ValidationError."""
        sheet = self._sc_sheet(period='2099-07-01')
        self._sc_line(sheet, self.emp, split_id=self.split.id,
                      achieved_sales=10_000.0)
        with self.assertRaises(ValidationError):
            self._sc_line(sheet, self.emp, split_id=self.split.id,
                          achieved_sales=15_000.0)

    def test_11_different_employees_no_constraint(self):
        """Two general lines for different employees on the same sheet → allowed."""
        sheet = self._sc_sheet(period='2099-08-01')
        la = self._sc_line(sheet, self.emp, achieved_sales=10_000.0)
        lb = self._sc_line(sheet, self.emp_b, achieved_sales=8_000.0)
        self.assertTrue(la and lb)

    # ==================================================================
    # 4. _get_profile_rule for split vs general lines
    # ==================================================================

    def test_12_split_line_uses_split_rule(self):
        """_get_profile_rule for split line → returns split.rule_id.

        target_sales is intentionally NOT passed so _compute_role_and_targets
        runs and sets role='sales' (from split.role), enabling _compute_commission
        to enter the sales block and populate sales_rule_id.
        """
        sheet = self._sc_sheet(period='2099-09-01')
        split_line = self._sc_line(sheet, self.emp, split_id=self.split.id,
                                   achieved_sales=20_000.0)
        # The computed split_rule used should be client_sales_rule
        # (split role='sales', so sales rule fires)
        self.assertEqual(split_line.sales_rule_id, self.client_sales_rule)

    def test_13_split_line_kind_mismatch_returns_no_collection_commission(self):
        """Split role=sales → collection commission must be 0 (kind mismatch)."""
        sheet = self._sc_sheet(period='2099-10-01')
        split_line = self._sc_line(sheet, self.emp, split_id=self.split.id,
                                   achieved_sales=20_000.0,
                                   achieved_coll=5_000.0,
                                   target_sales=20_000.0,
                                   target_coll=5_000.0)
        # split.role = 'sales', so collection block is not entered
        self.assertEqual(split_line.collection_commission_amount, 0.0)

    def test_14_general_line_uses_profile_explicit_sales_rule(self):
        """_get_profile_rule for general line retrieves profile.sales_rule_id."""
        sheet = self._sc_sheet(period='2099-11-01')
        line = self._sc_line(sheet, self.emp, achieved_sales=5_000.0)
        # profile.sales_rule_id = gen_sales_rule
        self.assertEqual(line.sales_rule_id, self.gen_sales_rule)

    # ==================================================================
    # 5. Commission calculation for split vs general lines
    # ==================================================================

    def test_15_split_line_commission_uses_split_rule_rate(self):
        """Split line commission = split rule rate applied to achieved."""
        # client_sales_rule: single tier 0% → ∞ @ 1% of target
        # Use target=100 000 to get a clean number
        sheet = self._sc_sheet(period='2099-12-01')
        split_line = self._sc_line(
            sheet, self.emp, split_id=self.split.id,
            achieved_sales=100_000.0,
            target_sales=100_000.0,
        )
        # 100% achievement, 1% rate, target base:
        # band 100 pts, tier_base = 100/100 * 100000 = 100000, rate 1% → 1000
        self.assertAlmostEqual(split_line.sales_commission_amount, 1_000.0, delta=1.0)

    def test_16_general_line_commission_independent_of_split(self):
        """General and split lines compute commission independently."""
        sheet = self._sc_sheet(period='2098-01-01')
        general = self._sc_line(sheet, self.emp,
                                achieved_sales=100_000.0,
                                target_sales=100_000.0,
                                target_coll=50_000.0,
                                role='sales')
        split_line = self._sc_line(sheet, self.emp, split_id=self.split.id,
                                   achieved_sales=40_000.0,
                                   target_sales=40_000.0)
        # Both lines have commission > 0 (achieved-base tier, rate is non-zero)
        self.assertGreater(general.sales_commission_amount, 0.0)
        self.assertGreater(split_line.sales_commission_amount, 0.0)
        # Tier base='achieved': commission = achieved_sales * rate_pct / 100
        # gen_sales_rule rate = 2%, split rule rate = 1%
        self.assertAlmostEqual(
            general.sales_commission_amount,
            100_000.0 * 0.02,  # achieved × 2% for gen_sales_rule
            delta=10.0,
        )
        self.assertAlmostEqual(
            split_line.sales_commission_amount,
            40_000.0 * 0.01,  # achieved × 1% for client_sales_rule
            delta=5.0,
        )

    def test_17_general_line_achieved_full_total_not_reduced(self):
        """General line achieved_sales can be set to the FULL total even when
        splits exist — the model imposes no automatic reduction.  The import
        wizard sets it to the full total; here we verify no validation error
        fires and the stored value is unchanged.
        """
        sheet = self._sc_sheet(period='2098-02-01')
        full_total = 150_000.0
        split_total = 40_000.0
        # Split line is set first with its clients' total
        self._sc_line(sheet, self.emp, split_id=self.split.id,
                      achieved_sales=split_total, target_sales=split_total)
        # General line stores the FULL total (not full_total - split_total)
        general = self._sc_line(sheet, self.emp, achieved_sales=full_total,
                                target_sales=full_total, role='sales')
        self.assertAlmostEqual(general.achieved_sales, full_total)

    # ==================================================================
    # 6. _resolve_rule: client & employee+client scopes
    # ==================================================================

    def test_18_resolve_rule_client_scope_matches_partner(self):
        """_resolve_rule returns client-scope rule when called with matching partner."""
        Rule = self.env['ksw.sales.commission.rule']
        # partner_a is in client_sales_rule.partner_ids
        found = Rule._resolve_rule(self.emp, 'sales', partner=self.partner_a)
        # employee_client scope (emp_client_rule) should beat client scope
        # because SCOPE_RANK employee_client=3 > client=1
        self.assertEqual(found, self.emp_client_rule)

    def test_19_resolve_rule_client_only_when_no_emp_client(self):
        """When no employee+client rule matches, client-scope rule is returned."""
        Rule = self.env['ksw.sales.commission.rule']
        # partner_b has client_sales_rule but NO emp_client_rule for emp
        found = Rule._resolve_rule(self.emp, 'sales', partner=self.partner_b)
        self.assertEqual(found, self.client_sales_rule)

    def test_20_resolve_rule_employee_client_beats_client(self):
        """employee+client scope rank (3) beats client scope (1)."""
        Rule = self.env['ksw.sales.commission.rule']
        # partner_a is in both client_sales_rule AND emp_client_rule for emp
        found = Rule._resolve_rule(self.emp, 'sales', partner=self.partner_a)
        self.assertEqual(found.scope, 'employee_client')

    def test_21_resolve_rule_no_partner_skips_client_scopes(self):
        """_resolve_rule without a partner does not return client-scoped rules."""
        Rule = self.env['ksw.sales.commission.rule']
        found = Rule._resolve_rule(self.emp, 'sales', partner=None)
        # Without a partner, client/employee_client scopes do not match
        self.assertNotEqual(found.scope if found else '', 'client')
        self.assertNotEqual(found.scope if found else '', 'employee_client')

    def test_22_resolve_rule_partner_c_no_client_rule(self):
        """partner_c not in any client rule → falls back to general rule."""
        Rule = self.env['ksw.sales.commission.rule']
        found = Rule._resolve_rule(self.emp, 'sales', partner=self.partner_c)
        # Only general / employee scopes match (partner_c not in any client rule)
        self.assertIn(found.scope if found else '', ('general', 'employee', ''))

    # ==================================================================
    # 7. x_collection_based_on_total flag on profile
    # ==================================================================

    def test_23_collection_based_on_total_default_false(self):
        """x_collection_based_on_total defaults to False."""
        self.assertFalse(self.profile.x_collection_based_on_total)

    def test_24_collection_based_on_total_can_be_set(self):
        """x_collection_based_on_total can be toggled on."""
        profile2 = self.env['ksw.salesperson.profile'].sudo().create({
            'employee_id': self.emp_b.id,
            'year': 2099,
            'role': 'collect',
            'annual_collection_target': 1_000_000.0,
            'x_collection_based_on_total': True,
        })
        self.assertTrue(profile2.x_collection_based_on_total)

    # ==================================================================
    # 8. res.partner new fields
    # ==================================================================

    def test_25_partner_has_x_client_account_number(self):
        """res.partner has x_client_account_number field."""
        p = self.env['res.partner'].sudo().create({
            'name': 'Field Test Partner', 'customer_rank': 1,
            'x_client_account_number': 'ACC-001',
        })
        self.assertEqual(p.x_client_account_number, 'ACC-001')

    def test_26_partner_has_x_commission_import_name(self):
        """res.partner has x_commission_import_name field."""
        p = self.env['res.partner'].sudo().create({
            'name': 'Import Name Partner', 'customer_rank': 1,
            'x_commission_import_name': 'ImportNameAlias',
        })
        self.assertEqual(p.x_commission_import_name, 'ImportNameAlias')

    def test_27_partner_account_number_independent_of_partner_name(self):
        """x_client_account_number is independent of partner name."""
        p = self.env['res.partner'].sudo().create({
            'name': 'Real Name SA', 'customer_rank': 1,
            'x_client_account_number': 'XYZ-9999',
        })
        p.sudo().write({'name': 'Updated Name SA'})
        p.invalidate_recordset()
        self.assertEqual(p.x_client_account_number, 'XYZ-9999')

    # ==================================================================
    # 9. Profile: split_ids cascade delete
    # ==================================================================

    def test_28_split_deleted_on_profile_unlink(self):
        """Deleting the profile also removes its split records (cascade)."""
        emp3 = self.env['hr.employee'].sudo().create({
            'name': 'Cascade Test Emp', 'x_is_attendance_sheet': True,
        })
        profile3 = self.env['ksw.salesperson.profile'].sudo().create({
            'employee_id': emp3.id,
            'year': 2099,
            'role': 'sales',
        })
        split3 = self.env['ksw.salesperson.profile.client.split'].sudo().create({
            'profile_id': profile3.id,
            'label': 'Cascade Split',
            'rule_id': self.client_sales_rule.id,
            'role': 'sales',
        })
        split3_id = split3.id
        profile3.sudo().unlink()
        remaining = self.env['ksw.salesperson.profile.client.split'].sudo().browse(
            split3_id).exists()
        self.assertFalse(remaining,
                         'Split record should be deleted when profile is deleted (cascade)')

    # ==================================================================
    # 10. split_label derived from split_id
    # ==================================================================

    def test_29_split_label_on_line_mirrors_split_label(self):
        """split_label on commission line is derived from split.label."""
        sheet = self._sc_sheet(period='2098-03-01')
        split_line = self._sc_line(sheet, self.emp, split_id=self.split.id)
        self.assertEqual(split_line.split_label, self.split.label)

    def test_30_split_label_blank_for_general_line(self):
        """split_label is blank for general (non-split) lines."""
        sheet = self._sc_sheet(period='2098-04-01')
        general = self._sc_line(sheet, self.emp)
        self.assertFalse(general.split_label)

    # ==================================================================
    # 11. Multiple splits on a single profile
    # ==================================================================

    def test_31_profile_can_have_multiple_splits(self):
        """A single profile can hold multiple distinct split entries."""
        rule_c = self._mk_rule(
            self.env, 'multi_split_c', kind='sales', scope='client',
            partners=[self.partner_c], tiers=[_tier(rate_pct=1.5)],
        )
        split_c = self.env['ksw.salesperson.profile.client.split'].sudo().create({
            'profile_id': self.profile.id,
            'label': 'Gamma Clients',
            'rule_id': rule_c.id,
            'role': 'sales',
        })
        self.assertEqual(len(self.profile.split_ids), 2)
        # Clean up
        split_c.sudo().unlink()

    def test_32_two_split_lines_different_splits_allowed(self):
        """Two split lines with different split_ids on same sheet → allowed."""
        rule_c = self._mk_rule(
            self.env, 'two_splits_c', kind='sales', scope='client',
            partners=[self.partner_c], tiers=[_tier(rate_pct=1.5)],
        )
        split_c = self.env['ksw.salesperson.profile.client.split'].sudo().create({
            'profile_id': self.profile.id,
            'label': 'C Split',
            'rule_id': rule_c.id,
            'role': 'sales',
        })
        sheet = self._sc_sheet(period='2098-05-01')
        line_ab = self._sc_line(sheet, self.emp, split_id=self.split.id,
                                achieved_sales=40_000.0)
        line_c = self._sc_line(sheet, self.emp, split_id=split_c.id,
                               achieved_sales=20_000.0)
        self.assertTrue(line_ab and line_c)
        # Clean up
        split_c.sudo().unlink()

    # ==================================================================
    # 12. Sales % and collection % for split line
    # ==================================================================

    def test_33_split_line_pct_computed_against_set_target(self):
        """sales_pct for split line uses target_sales when set via write().

        _compute_role_and_targets resets target_sales=0 on create (split lines
        have no meaningful target from the profile). However a supervisor/wizard
        can set target_sales via write(); this does NOT re-trigger the role
        compute (only split_id/employee/period do), so the value sticks and
        _compute_commission uses it for the sales_pct.
        """
        sheet = self._sc_sheet(period='2098-06-01')
        split_line = self._sc_line(
            sheet, self.emp, split_id=self.split.id,
            achieved_sales=60_000.0,
            # target_sales NOT provided — defaults to 0 after compute
        )
        # After create + invalidate, target_sales=0 → pct=0
        self.assertEqual(split_line.sales_pct, 0.0)
        # Now manually override target_sales via write()
        split_line.sudo().write({'target_sales': 100_000.0})
        split_line.invalidate_recordset()
        # _compute_commission fires because target_sales changed;
        # role compute deps (split_id, employee, period) unchanged → target stays
        self.assertAlmostEqual(split_line.sales_pct, 60.0, delta=0.5)

    def test_34_split_line_pct_zero_when_target_zero(self):
        """sales_pct = 0 when target_sales = 0 (split lines default target)."""
        sheet = self._sc_sheet(period='2098-07-01')
        split_line = self._sc_line(
            sheet, self.emp, split_id=self.split.id,
            achieved_sales=10_000.0,
            # target_sales not provided → defaults to 0
        )
        self.assertEqual(split_line.sales_pct, 0.0)








