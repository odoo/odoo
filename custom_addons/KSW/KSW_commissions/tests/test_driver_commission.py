"""Tests for ksw.driver.commission.sheet and ksw.driver.commission.line."""
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase
class TestDriverCommission(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env
        cls.site = env['ksw.site'].sudo().create({
            'name': 'Test Site Alpha', 'code': 'TSA',
            'required_trips_full_month': 50,
            'tier2_trips': 40, 'tier2_rate': 10.0,
            'tier3_trips': 40, 'tier3_rate': 15.0,
            'tier4_trips': 40, 'tier4_rate': 20.0,
            'tier5_rate': 25.0,
        })
        dept = env['hr.department'].create({'name': 'Driver Dept'})
        cls.emp1 = env['hr.employee'].sudo().create({
            'name': 'Driver One', 'department_id': dept.id,
            'x_is_attendance_sheet': True, 'x_site_id': cls.site.id,
        })
        cls.period = '2026-04-01'
    def _ds(self, **kw):
        v = dict(site_id=self.site.id, period=self.period)
        v.update(kw)
        return self.env['ksw.driver.commission.sheet'].sudo().create(v)
    def _line(self, sheet, emp, worked, trips, multiplied=None):
        """Create a driver commission line.

        ``multiplied`` sets ``multiplied_trips`` directly.
        When omitted it defaults to ``trips`` (actual = multiplied, no factor).
        """
        return self.env['ksw.driver.commission.line'].sudo().create({
            'sheet_id': sheet.id, 'employee_id': emp.id,
            'worked_days': worked, 'actual_trips': trips,
            'multiplied_trips': multiplied if multiplied is not None else trips,
        })
    def test_01_required_trips_full_month(self):
        ds = self._ds(); l = self._line(ds, self.emp1, 30, 0)
        self.assertEqual(l.required_trips, 50)
    def test_02_partial_month_pro_rata(self):
        ds = self._ds()
        l = self._line(ds, self.emp1, 19, 0)
        self.assertEqual(l.required_trips, round(50*19/30))
    def test_03_zero_commission_below_required(self):
        ds = self._ds(); l = self._line(ds, self.emp1, 30, 45)
        self.assertEqual(l.total_commission, 0.0)
    def test_04_tier2_only(self):
        ds = self._ds(); l = self._line(ds, self.emp1, 30, 60)
        self.assertEqual(l.tier2_trips, 10)
        self.assertAlmostEqual(l.total_commission, 100.0)
    def test_05_tiers_2_and_3(self):
        ds = self._ds(); l = self._line(ds, self.emp1, 30, 130)
        self.assertEqual(l.tier2_trips, 40); self.assertEqual(l.tier3_trips, 40)
        self.assertAlmostEqual(l.total_commission, 40*10 + 40*15)
    def test_06_all_five_tiers(self):
        ds = self._ds(); l = self._line(ds, self.emp1, 30, 190)
        self.assertEqual(l.tier5_trips, 20)
        self.assertAlmostEqual(l.total_commission, 40*10+40*15+40*20+20*25)
    def test_07_multiplier_applied(self):
        """Setting multiplied_trips independently of actual_trips works."""
        ds = self._ds()
        l = self._line(ds, self.emp1, 30, 40, multiplied=60)
        self.assertEqual(l.multiplied_trips, 60)
        # required=50, above=max(60-50,0)=10, tier2 rate=10 → 1 tier-2 trip × 10 = 100
        self.assertAlmostEqual(l.total_commission, 100.0)
    def test_08_confirm_sets_state(self):
        ds = self._ds(); self._line(ds, self.emp1, 30, 60)
        ds.action_confirm()
        self.assertEqual(ds.state, 'confirmed')
    def test_09_unique_site_period(self):
        self._ds()
        with self.assertRaises(Exception):
            self._ds()
    def test_10_sheet_total_is_sum_of_lines(self):
        ds = self._ds()
        emp2 = self.env['hr.employee'].sudo().create({
            'name': 'Driver Two', 'x_is_attendance_sheet': True,
        })
        self._line(ds, self.emp1, 30, 60)  # 100 SAR
        self._line(ds, emp2, 30, 60)       # 100 SAR
        self.assertAlmostEqual(ds.total_commission, 200.0)
