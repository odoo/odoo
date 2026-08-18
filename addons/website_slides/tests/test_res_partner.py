from odoo.addons.website_slides.tests import common as slides_common


class TestPartner(slides_common.SlidesCase):
    def test_descendants_courses(self):
        """ Test the Courses smart button has all courses from itself and all descendants."""

        parent_company = self.env['res.partner'].create({
            'name': 'Parent Company',
            'is_company': True,
        })
        child_company = self.env['res.partner'].create({
            'name': 'Child Company',
            'is_company': True,
            'parent_id': parent_company.id,
        })
        parent_individual = self.env['res.partner'].create({
            'name': 'Parent Individual',
            'parent_id': child_company.id,
        })
        child_individual = self.env['res.partner'].create({
            'name': 'Child Individual',
            'parent_id': parent_individual.id,
        })

        course_a = self.channel
        course_b, course_c, course_d = self.env['slide.channel'].create([{
            'name': 'Test Channel B',
            'is_published': True,
        }, {
            'name': 'Test Channel C',
            'is_published': True,
        }, {
            'name': 'Test Channel D',
            'is_published': True,
        }])

        course_a.action_grant_access(parent_company.id)
        course_b.action_grant_access(child_company.id)
        course_c.action_grant_access(parent_individual.id)
        course_d.action_grant_access(child_individual.id)

        self.assertRecordValues(parent_company | child_company | parent_individual | child_individual, [
            {'slide_channel_company_count': 4},
            {'slide_channel_company_count': 3},
            {'slide_channel_company_count': 2},
            {'slide_channel_company_count': 1},
        ])

        action = parent_company.action_view_courses()
        domain = action.get('domain', [])
        enrollments = self.env[action['res_model']].search(domain)
        courses_in_action = enrollments.mapped('channel_id')
        self.assertEqual(courses_in_action, course_a | course_b | course_c | course_d)

        action = parent_individual.action_view_courses()
        domain = action.get('domain', [])
        enrollments = self.env[action['res_model']].search(domain)
        courses_in_action = enrollments.mapped('channel_id')
        self.assertEqual(courses_in_action, course_c | course_d)
