# Part of Odoo. See LICENSE file for full copyright and licensing details.
"""Unit tests for the SRU mapping parser and account matching logic."""

from odoo.tests import TransactionCase, tagged

from odoo.addons.l10n_se.models.l10n_se_sru_mapping import (
    _matches,
    _parse_expression,
    _parse_item,
    _resolve_sru_code,
)


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestSruParser(TransactionCase):
    """Tests for the BAS account expression parser."""

    # --- _parse_item ---

    def test_parse_item_single_account(self):
        """A plain 4-digit code parses as a prefix item."""
        self.assertEqual(_parse_item('1510'), ('prefix', '1510'))

    def test_parse_item_wildcard_trailing(self):
        """A code ending in x parses as a prefix item."""
        self.assertEqual(_parse_item('15xx'), ('prefix', '15xx'))

    def test_parse_item_wildcard_middle(self):
        """A wildcard anywhere in a prefix is accepted, not just trailing."""
        self.assertEqual(_parse_item('1x10'), ('prefix', '1x10'))

    def test_parse_item_range(self):
        """A low..high expression parses as a range item."""
        self.assertEqual(_parse_item('10..19'), ('range', '10', '19'))

    def test_parse_item_range_4digit(self):
        """A 4-digit range parses correctly."""
        self.assertEqual(_parse_item('1000..1087'), ('range', '1000', '1087'))

    def test_parse_item_range_wildcard_bounds(self):
        """Wildcards are accepted anywhere in either range bound."""
        self.assertEqual(_parse_item('1x10..1x20'), ('range', '1x10', '1x20'))

    def test_parse_item_strips_whitespace(self):
        """Whitespace around an item is stripped."""
        self.assertEqual(_parse_item(' 1510 '), ('prefix', '1510'))

    def test_parse_item_uppercase_wildcard(self):
        """An uppercase X is normalized, so '15XX' matches like '15xx'."""
        self.assertEqual(_parse_item('15XX'), ('prefix', '15xx'))
        self.assertTrue(_matches('1510', 'D', '15XX'))

    def test_parse_item_invalid_returns_none(self):
        """An item with characters other than digits/x is rejected."""
        self.assertIsNone(_parse_item('15a0'))
        self.assertIsNone(_parse_item(''))

    # --- _parse_expression: basic ---

    def test_parse_expression_empty_returns_none(self):
        """Empty expression returns None."""
        self.assertIsNone(_parse_expression(''))
        self.assertIsNone(_parse_expression('   '))

    def test_parse_expression_single_prefix(self):
        """A single prefix expression parses correctly."""
        p = _parse_expression('15xx')
        self.assertIsNone(p['direction'])
        self.assertEqual(p['includes'], [('prefix', '15xx')])
        self.assertEqual(p['excludes'], [])

    def test_parse_expression_single_4digit(self):
        """A single 4-digit code parses correctly."""
        p = _parse_expression('1088')
        self.assertIsNone(p['direction'])
        self.assertEqual(p['includes'], [('prefix', '1088')])

    def test_parse_expression_dotdot_range(self):
        """A low..high expression parses as a range include."""
        p = _parse_expression('1000..1087')
        self.assertEqual(p['includes'], [('range', '1000', '1087')])
        self.assertEqual(p['excludes'], [])

    # --- _parse_expression: direction ---

    def test_parse_expression_direction_C(self):
        """C prefix sets direction to C."""
        p = _parse_expression('C80..82')
        self.assertEqual(p['direction'], 'C')

    def test_parse_expression_direction_D(self):
        """D prefix sets direction to D."""
        p = _parse_expression('D49xx')
        self.assertEqual(p['direction'], 'D')

    def test_parse_expression_lowercase_direction(self):
        """Lowercase c/d direction prefix is accepted."""
        p = _parse_expression('c15xx')
        self.assertEqual(p['direction'], 'C')

    # --- _parse_expression: comma-separated include/exclude lists ---

    def test_parse_expression_multiple_includes(self):
        """Comma adds another independent include item."""
        p = _parse_expression('101x..109x,1102')
        self.assertEqual(
            p['includes'],
            [('range', '101x', '109x'), ('prefix', '1102')],
        )
        self.assertEqual(p['excludes'], [])

    def test_parse_expression_single_exclude(self):
        """A single item after the dash is an exclude."""
        p = _parse_expression('10..19-1088')
        self.assertEqual(p['includes'], [('range', '10', '19')])
        self.assertEqual(p['excludes'], [('prefix', '1088')])

    def test_parse_expression_multiple_excludes_need_commas(self):
        """Multiple excludes after the dash must be comma-separated."""
        p = _parse_expression('C80..82-807x,808x')
        self.assertEqual(p['direction'], 'C')
        self.assertEqual(p['includes'], [('range', '80', '82')])
        self.assertEqual(len(p['excludes']), 2)
        self.assertIn(('prefix', '807x'), p['excludes'])
        self.assertIn(('prefix', '808x'), p['excludes'])

    def test_parse_expression_only_first_dash_switches_mode(self):
        """A second, unquoted dash inside the exclude list is not a new
        separator - it makes that item invalid and it's dropped, rather
        than starting a third list."""
        p = _parse_expression('C80..82-807x-808x')
        self.assertEqual(p['includes'], [('range', '80', '82')])
        self.assertEqual(p['excludes'], [])

    def test_parse_expression_full_example(self):
        """The include/exclude example from the field's help text."""
        p = _parse_expression('101x..109x,1102-1015..1019,1021')
        self.assertEqual(
            p['includes'],
            [('range', '101x', '109x'), ('prefix', '1102')],
        )
        self.assertEqual(
            p['excludes'],
            [('range', '1015', '1019'), ('prefix', '1021')],
        )

    # --- _matches: basic prefix ---

    def test_matches_exact_code(self):
        """Exact 4-digit code matches itself."""
        self.assertTrue(_matches('1510', '', '1510'))

    def test_matches_exact_code_no_match(self):
        """Exact code does not match a different code."""
        self.assertFalse(_matches('1511', '', '1510'))

    def test_matches_wildcard_xx(self):
        """xx wildcard matches any 2 trailing digits."""
        self.assertTrue(_matches('1510', '', '15xx'))
        self.assertTrue(_matches('1599', '', '15xx'))
        self.assertFalse(_matches('1610', '', '15xx'))

    def test_matches_wildcard_x(self):
        """x wildcard matches any trailing digit."""
        self.assertTrue(_matches('1510', '', '151x'))
        self.assertTrue(_matches('1519', '', '151x'))
        self.assertFalse(_matches('1520', '', '151x'))

    def test_matches_wildcard_middle_position(self):
        """A wildcard in the middle of a prefix matches any digit there."""
        self.assertTrue(_matches('1010', '', '1x10'))
        self.assertTrue(_matches('1910', '', '1x10'))
        self.assertFalse(_matches('1015', '', '1x10'))

    # --- _matches: dotdot range ---

    def test_matches_dotdot_range_inside(self):
        """Account inside a dotdot range matches."""
        self.assertTrue(_matches('1510', '', '15..16'))

    def test_matches_dotdot_range_boundary(self):
        """Accounts at range boundaries match."""
        self.assertTrue(_matches('1500', '', '15..16'))
        self.assertTrue(_matches('1699', '', '15..16'))

    def test_matches_dotdot_range_outside(self):
        """Account outside a dotdot range does not match."""
        self.assertFalse(_matches('1700', '', '15..16'))
        self.assertFalse(_matches('1499', '', '15..16'))

    def test_matches_4digit_dotdot_range(self):
        """4-digit dotdot range matches correctly."""
        self.assertTrue(_matches('1050', '', '1000..1087'))
        self.assertFalse(_matches('1088', '', '1000..1087'))
        self.assertFalse(_matches('0999', '', '1000..1087'))

    def test_matches_wildcard_range(self):
        """A wildcard-bounded range covers its full numeric interval."""
        self.assertTrue(_matches('3000', '', '30xx..37xx'))
        self.assertTrue(_matches('3799', '', '30xx..37xx'))
        self.assertFalse(_matches('3800', '', '30xx..37xx'))
        self.assertFalse(_matches('2999', '', '30xx..37xx'))

    def test_matches_wildcard_range_x_suffix(self):
        """A single-x wildcard range matches its full interval."""
        self.assertTrue(_matches('1210', '', '121x..128x'))
        self.assertTrue(_matches('1289', '', '121x..128x'))
        self.assertFalse(_matches('1290', '', '121x..128x'))
        self.assertFalse(_matches('1209', '', '121x..128x'))

    # --- _matches: exclusions ---

    def test_matches_excludes_specific_code(self):
        """Excluded 4-digit code does not match."""
        self.assertFalse(_matches('1088', '', '10..19-1088'))
        self.assertTrue(_matches('1087', '', '10..19-1088'))

    def test_matches_excludes_multiple_wildcards(self):
        """Multiple comma-separated wildcard exclusions all apply."""
        self.assertFalse(_matches('8070', '', 'C80..82-807x,808x'))
        self.assertFalse(_matches('8080', '', 'C80..82-807x,808x'))
        self.assertTrue(_matches('8050', '', 'C80..82-807x,808x'))

    # --- _matches: direction ---

    def test_direction_C_matches_C(self):
        """C expression matches C direction."""
        self.assertTrue(_matches('8050', 'C', 'C80..82'))

    def test_direction_C_no_match_D(self):
        """C expression does not match D direction."""
        self.assertFalse(_matches('8050', 'D', 'C80..82'))

    def test_direction_D_matches_D(self):
        """D expression matches D direction."""
        self.assertTrue(_matches('4900', 'D', 'D49xx'))

    def test_direction_D_no_match_C(self):
        """D expression does not match C direction."""
        self.assertFalse(_matches('4900', 'C', 'D49xx'))

    def test_no_direction_matches_C(self):
        """Expression without direction matches C."""
        self.assertTrue(_matches('1510', 'C', '15xx'))

    def test_no_direction_matches_D(self):
        """Expression without direction matches D."""
        self.assertTrue(_matches('1510', 'D', '15xx'))

    def test_no_direction_matches_empty(self):
        """Expression without direction matches empty direction."""
        self.assertTrue(_matches('1510', '', '15xx'))

    # --- Real-world INK2 expressions (post-migration, ".." syntax) ---

    def test_ink2_nettoomsattning(self):
        """30xx..37xx matches all revenue accounts."""
        for code in ['3000', '3100', '3500', '3799']:
            self.assertTrue(_matches(code, '', '30xx..37xx'), f"Expected match for {code}")
        self.assertFalse(_matches('3800', '', '30xx..37xx'))
        self.assertFalse(_matches('2999', '', '30xx..37xx'))

    def test_ink2_ovriga_externa_kostnader(self):
        """50xx..69xx matches external costs."""
        for code in ['5000', '5500', '6000', '6999']:
            self.assertTrue(_matches(code, '', '50xx..69xx'), f"Expected match for {code}")
        self.assertFalse(_matches('4999', '', '50xx..69xx'))
        self.assertFalse(_matches('7000', '', '50xx..69xx'))

    def test_ink2_personalkostnader(self):
        """70xx..76xx matches personnel costs."""
        self.assertTrue(_matches('7000', '', '70xx..76xx'))
        self.assertTrue(_matches('7699', '', '70xx..76xx'))
        self.assertFalse(_matches('7700', '', '70xx..76xx'))

    def test_ink2_avskrivningar_range(self):
        """7700..7739 matches depreciation accounts."""
        self.assertTrue(_matches('7700', '', '7700..7739'))
        self.assertTrue(_matches('7739', '', '7700..7739'))
        self.assertFalse(_matches('7740', '', '7700..7739'))

    def test_ink2_resultat_koncern_positive(self):
        """8000..8069 without direction prefix matches any direction.

        Direction (C->7414, D->7518) is set by the SRU code chosen for
        that row in the CSV, not by the account_expression itself.
        """
        self.assertTrue(_matches('8000', 'C', '8000..8069'))
        self.assertTrue(_matches('8069', 'C', '8000..8069'))
        self.assertFalse(_matches('8070', 'C', '8000..8069'))
        self.assertTrue(_matches('8000', 'D', '8000..8069'))

    def test_ink2_arets_resultat(self):
        """899x without direction prefix matches any direction.

        Direction filtering (C->7450, D->7550) is handled by having two
        separate mapping rows with C/D-prefixed expressions, not by
        this bare expression.
        """
        self.assertTrue(_matches('8990', 'C', '899x'))
        self.assertTrue(_matches('8990', 'D', '899x'))
        self.assertTrue(_matches('8990', '', '899x'))

    def test_ink2_varulager(self):
        """141x..142x range matches inventory accounts."""
        self.assertTrue(_matches('1410', '', '141x..142x'))
        self.assertTrue(_matches('1429', '', '141x..142x'))
        self.assertFalse(_matches('1430', '', '141x..142x'))
        self.assertFalse(_matches('1409', '', '141x..142x'))

    def test_ink2_kundfordringar(self):
        """151x..155x range matches receivables."""
        self.assertTrue(_matches('1510', '', '151x..155x'))
        self.assertTrue(_matches('1559', '', '151x..155x'))
        self.assertFalse(_matches('1560', '', '151x..155x'))


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestGetSruCodes(TransactionCase):
    """Tests for the get_sru_codes() method logic (direction from balance)."""

    def _resolve(self, account_code, balance, mappings_data):
        """Helper: simulate get_sru_codes for a single account."""

        class FakeMapping:
            def __init__(self, expr, code):
                self.account_expression = expr
                self.sru_code = code

        mappings = [FakeMapping(expr, code) for expr, code in mappings_data]
        if not balance:
            return None
        direction = 'D' if balance > 0 else 'C'
        return _resolve_sru_code(account_code, direction, mappings)

    def test_positive_balance_gives_D(self):
        """Positive balance maps to D direction."""
        result = self._resolve('1510', 25000.0, [('15xx', '7251')])
        self.assertEqual(result, '7251')

    def test_negative_balance_gives_C(self):
        """Negative balance maps to C direction."""
        result = self._resolve('8990', -150000.0, [('C899x', '7450')])
        self.assertEqual(result, '7450')

    def test_negative_balance_D_expression_no_match(self):
        """Negative balance does not match a D expression."""
        result = self._resolve('8990', -150000.0, [('D899x', '7550')])
        self.assertIsNone(result)

    def test_positive_balance_C_expression_no_match(self):
        """Positive balance does not match a C expression."""
        result = self._resolve('8990', 150000.0, [('C899x', '7450')])
        self.assertIsNone(result)

    def test_zero_balance_returns_none(self):
        """Zero balance returns None."""
        result = self._resolve('1510', 0.0, [('15xx', '7251')])
        self.assertIsNone(result)

    def test_loss_maps_to_D_sru(self):
        """Debit balance on 899x maps to the D SRU code (loss)."""
        result = self._resolve('8990', 50000.0, [('D899x', '7550')])
        self.assertEqual(result, '7550')

    def test_profit_maps_to_C_sru(self):
        """Credit balance on 899x maps to the C SRU code (profit)."""
        result = self._resolve('8990', -50000.0, [('C899x', '7450')])
        self.assertEqual(result, '7450')

    def test_no_matching_expression_returns_none(self):
        """Account with no matching expression returns None."""
        result = self._resolve('9999', 1000.0, [('15xx', '7251')])
        self.assertIsNone(result)


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestBundledSruTemplates(TransactionCase):
    """Regression tests against the actual bundled CSV templates.

    Unlike TestSruParser, which tests the grammar in isolation, these
    tests load the real template files via load_template_from_file()
    and check that specific, known-important accounts resolve to the
    SRU code confirmed against BAS.se's own INK2/INK3/INK4 kopplingsfiler
    (see module changelog for source revisions). These exist because a
    C/D direction inversion previously shipped silently in these exact
    templates - a swap that no expression-level unit test could catch,
    since each individual row was syntactically valid and its own
    _matches() behaviour was correct in isolation. Only checking the
    *resolved* SRU code for real accounts against the real templates
    catches that class of bug.
    """

    def _load(self, sru_type):
        self.assertTrue(self.env['l10n_se.sru.mapping'].load_template_from_file(sru_type))
        return self.env['l10n_se.sru.mapping'].search([
            ('company_id', '=', self.env.company.id),
            ('sru_type', '=', sru_type),
        ])

    def _resolve(self, mappings, account_code, direction):
        return _resolve_sru_code(account_code, direction, mappings)

    def test_ink2_profit_loss_direction_not_swapped(self):
        """8990 (Arets resultat) must resolve profit->7450, loss->7550.

        This is the single most consequential figure on the whole INK2
        form. A C/D swap here previously reported every profit as a
        loss and vice versa.
        """
        mappings = self._load('ink2')
        self.assertEqual(self._resolve(mappings, '8990', 'D'), '7450',
                          "Debit balance (profit, netto+) must map to 7450")
        self.assertEqual(self._resolve(mappings, '8990', 'C'), '7550',
                          "Credit balance (loss, netto-) must map to 7550")

    def test_ink2_split_pairs_not_swapped(self):
        """Spot-check every C/D split pair present in the ink2 template.

        For result accounts a credit balance increases the result and goes to
        the "+" field (e.g. an inventory increase or a dividend received), a
        debit balance goes to the "-" field. 899x is the exception, see above.
        """
        mappings = self._load('ink2')
        pairs = [
            # account, expected_D ("-" field), expected_C ("+" field)
            ('4900', '7510', '7411'),   # net 49xx
            ('8010', '7518', '7414'),   # net 80xx
            ('8100', '7519', '7415'),   # net 81xx
            ('8200', '7520', '7416'),   # net 82xx
            ('8810', '7525', '7420'),   # avsattning/aterforing periodiseringsfond
            ('8850', '7526', '7421'),   # net 885x
            ('8860', '7527', '7422'),   # net 886x-889x
        ]
        for account, expected_D, expected_C in pairs:
            with self.subTest(account=account):
                self.assertEqual(self._resolve(mappings, account, 'D'), expected_D)
                self.assertEqual(self._resolve(mappings, account, 'C'), expected_C)

    def test_ink3_split_pairs_not_swapped(self):
        """Spot-check the C/D split pairs in the ink3 template."""
        mappings = self._load('ink3')
        pairs = [
            # account, expected_D ("-" field), expected_C ("+" field)
            ('8010', '8755', '8655'),   # net 801x-803x/811x-813x
            ('8210', '8756', '8656'),   # net 821x-826x/829x
            ('8810', '8760', '8659'),   # avsattning/aterforing periodiseringsfond
            ('8850', '8761', '8660'),   # ovriga bokslutsdispositioner
        ]
        for account, expected_D, expected_C in pairs:
            with self.subTest(account=account):
                self.assertEqual(self._resolve(mappings, account, 'D'), expected_D)
                self.assertEqual(self._resolve(mappings, account, 'C'), expected_C)

    def test_ink4_profit_loss_direction_not_swapped(self):
        """8990 must resolve profit->7450, loss->7550 in ink4 too."""
        mappings = self._load('ink4')
        self.assertEqual(self._resolve(mappings, '8990', 'D'), '7450')
        self.assertEqual(self._resolve(mappings, '8990', 'C'), '7550')

    def test_ink4_split_pairs_not_swapped(self):
        """Spot-check the C/D split pairs in the ink4 template."""
        mappings = self._load('ink4')
        pairs = [
            # account, expected_D ("-" field), expected_C ("+" field)
            ('4900', '7510', '7411'),
            ('8010', '7518', '7414'),
            ('8100', '7519', '7415'),
            ('8200', '7520', '7416'),
            ('8800', '7537', '7427'),
        ]
        for account, expected_D, expected_C in pairs:
            with self.subTest(account=account):
                self.assertEqual(self._resolve(mappings, account, 'D'), expected_D)
                self.assertEqual(self._resolve(mappings, account, 'C'), expected_C)

    def test_ink2_no_unmapped_gap_around_previously_missing_rows(self):
        """Accounts that were previously silently unmapped now resolve."""
        mappings = self._load('ink2')
        self.assertEqual(self._resolve(mappings, '1575', 'D'), '7252')
        self.assertEqual(self._resolve(mappings, '1675', 'D'), '7252')
        self.assertEqual(self._resolve(mappings, '2865', 'D'), '7367')
        self.assertEqual(self._resolve(mappings, '2473', 'D'), '7369')
        self.assertEqual(self._resolve(mappings, '2873', 'D'), '7369')
        self.assertEqual(self._resolve(mappings, '4925', 'D'), '7511')

    def test_unconditional_appropriation_accounts(self):
        """Accounts BAS maps without a sign condition resolve in both directions."""
        ink2 = self._load('ink2')
        for direction in 'DC':
            with self.subTest(direction=direction):
                self.assertEqual(self._resolve(ink2, '8811', direction), '7525')  # avsattning periodiseringsfond
                self.assertEqual(self._resolve(ink2, '8819', direction), '7420')  # aterforing periodiseringsfond
        ink3 = self._load('ink3')
        self.assertEqual(self._resolve(ink3, '8820', 'C'), '8660')  # mottagna koncernbidrag
        self.assertEqual(self._resolve(ink3, '8830', 'D'), '8761')  # lamnade koncernbidrag

    def test_skatteverket_2026p4_fields(self):
        """Field codes and directions checked against Skatteverket's field tables for 2026P4."""
        ink3 = self._load('ink3')
        self.assertEqual(self._resolve(ink3, '8999', 'D'), '8663')  # 6.20 arets resultat, vinst
        self.assertEqual(self._resolve(ink3, '8999', 'C'), '8763')  # 6.20 arets resultat, forlust
        ink4 = self._load('ink4')
        for account in ('2019', '2029', '2039', '2049'):
            with self.subTest(account=account):
                self.assertEqual(self._resolve(ink4, account, 'C'), '7312')  # 2.21 arets redovisade vinst
                self.assertEqual(self._resolve(ink4, account, 'D'), '7313')  # 2.22 arets redovisade forlust
        ne = self._load('ne')
        self.assertEqual(self._resolve(ne, '3000', 'C'), '7400')  # R1 momspliktiga intakter
        self.assertEqual(self._resolve(ne, '3100', 'C'), '7401')  # R2 momsfria intakter
        self.assertEqual(self._resolve(ne, '3200', 'C'), '7402')  # R3 bil- och bostadsforman
        for account in ('2610', '2650', '2660', '2710', '2730'):
            with self.subTest(account=account):
                self.assertEqual(self._resolve(ne, account, 'C'), '7381')  # B14 skatteskulder
        self.assertEqual(self._resolve(ne, '2900', 'C'), '7383')  # B16 ovriga skulder

    def test_goods_for_resale_and_raw_materials_split(self):
        """BAS 2026: 40xx-42xx are goods for resale, 43xx-48xx raw materials and consumables."""
        mappings = self._load('ink2')
        for account, expected in (('4010', '7512'), ('4210', '7512'), ('4310', '7511'), ('4535', '7511'), ('4810', '7511')):
            with self.subTest(account=account):
                self.assertEqual(self._resolve(mappings, account, 'D'), expected)

    def test_sequence_field_controls_order(self):
        """Rows loaded from the template get an explicit, increasing sequence."""
        mappings = self._load('ink2')
        sequences = mappings.mapped('sequence')
        self.assertEqual(sequences, sorted(sequences),
                          "search() should return rows in sequence order")
        self.assertEqual(len(sequences), len(set(sequences)),
                          "template rows should get distinct sequence values")

    def test_ne_interest_split_income_is_C_cost_is_D(self):
        """NE's 7403/7503 split follows income=C, cost=D (not the naive +/- read).

        Confirmed: a credit-heavy (income) balance on a mixed interest
        account maps to C direction -> 7403 (Ranteintakter), and a
        debit-heavy (cost) balance maps to D direction -> 7503
        (Rantekostnader). This is the reverse of mapping the source's
        "(+)"/"(-)" symbols directly onto C/D.
        """
        mappings = self._load('ne')
        for account in ['8020', '8030', '8120', '8130', '8220', '8230',
                         '8240', '8290', '8320', '8330', '8350', '8430',
                         '8450', '8490', '8810', '8860', '8880', '8890']:
            with self.subTest(account=account):
                self.assertEqual(self._resolve(mappings, account, 'C'), '7403')
                self.assertEqual(self._resolve(mappings, account, 'D'), '7503')

    def test_ne_unconditional_interest_accounts(self):
        """NE accounts with no source marker map regardless of direction."""
        mappings = self._load('ne')
        pairs = [
            ('3800', '7403'), ('8010', '7403'),
            ('7740', '7503'), ('7900', '7503'), ('8070', '7503'), ('8180', '7503'),
        ]
        for account, expected in pairs:
            with self.subTest(account=account):
                self.assertEqual(self._resolve(mappings, account, 'C'), expected)
                self.assertEqual(self._resolve(mappings, account, 'D'), expected)

    def test_ne_899x_excluded_from_rantekostnader(self):
        """899x (arets resultat) is excluded from 7503's 89xx range."""
        mappings = self._load('ne')
        self.assertEqual(self._resolve(mappings, '8990', 'C'), '7440')
        self.assertEqual(self._resolve(mappings, '8990', 'D'), '7440')
