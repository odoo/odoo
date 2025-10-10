# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import tagged, TransactionCase


@tagged('geo_fence_attendance')
class TestGeoFenceAttendance(TransactionCase):

    def setUp(self):
        super().setUp()
        self.company = self.env['res.company'].create({
            'name': 'Test Company',
            'workplace_location': '19.0760,72.8777',
            'workplace_latitude': 19.0760,
            'workplace_longitude': 72.8777,
            'workplace_radius': 5000.0,  # 5000 meters radius
            'geo_fence_attendance': True,
        })
        self.employee = self.env['hr.employee'].create({
            'name': 'John Doe',
            'company_id': self.company.id,
        })
        self.employee.company_id.workplace_latitude = self.company.workplace_latitude
        self.employee.company_id.workplace_longitude = self.company.workplace_longitude
        self.employee.company_id.workplace_radius = self.company.workplace_radius
        self.employee.company_id.geo_fence_attendance = self.company.geo_fence_attendance

    def test_calculate_employee_distance_from_workplace_within_radius(self):
        """Test Haversine distance calculation for a location within the workplace radius."""
        # A location near the workplace (Mumbai, India)
        lat = 19.075983
        long = 72.877655
        distance = self.employee._calculate_employee_distance_from_workplace(lat, long)
        self.assertLess(distance, self.company.workplace_radius)

    def test_calculate_employee_distance_from_workplace_outside_radius(self):
        """Test Haversine distance calculation for a location outside the workplace radius."""
        # A location far from the workplace (New Delhi, India)
        lat = 28.7041
        long = 77.1025
        distance = self.employee._calculate_employee_distance_from_workplace(lat, long)
        self.assertGreater(distance, self.company.workplace_radius)

    def test_check_in_within_geo_fence(self):
        """Test check-in when the employee is within the geo-fence."""
        geo_information = {
            'latitude': 19.0959,
            'longitude': 72.8776,
        }
        attendance = self.employee._attendance_action_change(geo_information=geo_information)
        self.assertFalse(attendance.outside_geo_fence, "Employee should not be flagged as outside the geo-fence.")
        self.assertEqual(attendance.employee_id.id, self.employee.id)
        self.assertIsNotNone(attendance.check_in)
        self.assertEqual(attendance.in_latitude, geo_information['latitude'])
        self.assertEqual(attendance.in_longitude, geo_information['longitude'])

    def test_check_in_outside_geo_fence_flagged(self):
        """Test check-in when the employee is outside the geo-fence, and the flag should be set."""
        geo_information = {
            'latitude': 23.1931904,
            'longitude': 72.6007808,
        }
        attendance = self.employee._attendance_action_change(geo_information=geo_information)
        self.assertTrue(attendance.outside_geo_fence, "Employee should be flagged as outside the geo-fence.")
        self.assertEqual(attendance.employee_id.id, self.employee.id)
        self.assertIsNotNone(attendance.check_in)
        self.assertEqual(attendance.in_latitude, geo_information['latitude'])
        self.assertEqual(attendance.in_longitude, geo_information['longitude'])
