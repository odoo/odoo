# # -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json

from odoo.exceptions import UserError
from odoo.addons.hr_referral.tests.common import TestHrReferralBase


class TestHrReferral(TestHrReferralBase):

    def test_referral_share_is_new(self):
        self.job_dev = self.job_dev.with_user(self.richard_user.id)

        self.env['hr.referral.link.to.share'].with_user(self.richard_user.id).create({'job_id': self.job_dev.id}).url
        links = self.env['link.tracker'].search([('campaign_id', '=', self.job_dev.utm_campaign_id.id)])
        self.assertEqual(len(links), 1, "It should have created only one link tracker")

        self.env['hr.referral.link.to.share'].with_user(self.steve_user.id).create({'job_id': self.job_dev.id}).url
        links = self.env['link.tracker'].search([('campaign_id', '=', self.job_dev.utm_campaign_id.id)])
        self.assertEqual(len(links), 2, "It should have created 2 different links tracker (one for each user)")

    def test_referral_change_referrer(self):
        # Create an applicant
        job_applicant = self.env['hr.applicant'].create({
            'name': 'Technical worker',
            'description': 'A nice job offer!',
            'job_id': self.job_dev.id,
            'ref_user_id': self.richard_user.id
        })
        self.assertEqual(job_applicant.ref_user_id, self.richard_user, "Referral is created with the right user")
        points_richard = self.env['hr.referral.points'].search([('ref_user_id', '=', self.richard_user.id)])
        self.assertEqual(job_applicant.stage_id.points, sum(points_richard.mapped('points')), "Right amount of referral points are created.")
        # We change the referrer on the job applicant, Richard will lose all his points and Steve will get points
        job_applicant.ref_user_id = self.steve_user.id
        self.assertEqual(job_applicant.ref_user_id, self.steve_user, "Referral is modified with as user Steve")
        points_richard = self.env['hr.referral.points'].search([('ref_user_id', '=', self.richard_user.id)])
        self.assertEqual(sum(points_richard.mapped('points')), 0, "Richard has no more points")
        points_steve = self.env['hr.referral.points'].search([('ref_user_id', '=', self.steve_user.id)])
        self.assertEqual(sum(points_steve.mapped('points')), job_applicant.stage_id.points, "Right amount of referral points are created for Steve")

    def test_referral_add_points(self):
        with self.assertRaises(UserError):
            self.mug_shop.sudo().buy()
        job_applicant = self.env['hr.applicant'].create({
            'name': 'Technical worker',
            'description': 'A nice applicant!',
            'job_id': self.job_dev.id,
            'ref_user_id': self.richard_user.id,
            'company_id': self.company_1.id
        })
        self.assertEqual(job_applicant.earned_points, job_applicant.stage_id.points, "Richard received points corresponding to the first stage.")
        stages = self.env['hr.recruitment.stage'].search([('job_ids', '=', False)])
        # We jump some stages of process, multiple points must be given
        job_applicant.stage_id = stages[-2]
        self.assertEqual(job_applicant.earned_points, sum(stages[:-1].mapped('points')), "Richard received points corresponding to the before last stage.")
        self.assertEqual(job_applicant.referral_state, 'progress', "Referral stay in progress")
        job_applicant.stage_id = stages[-1]
        self.assertEqual(job_applicant.earned_points, sum(stages.mapped('points')), "Richard received points corresponding to the last stage.")
        self.assertEqual(job_applicant.referral_state, 'hired', "Referral is hired")
        self.mug_shop.sudo().buy()
        shopped_item = self.env['hr.referral.points'].search([('ref_user_id', '=', self.richard_user.id), ('hr_referral_reward_id', '!=', False)])
        self.assertEqual(shopped_item.points, -self.mug_shop.cost, "The item bought decrease the number of points.")

    def test_referral_multi_company(self):
        self.job_dev = self.job_dev.with_user(self.richard_user.id)
        self.env['hr.referral.link.to.share'].with_user(self.richard_user.id).create({'job_id': self.job_dev.id}).url

        job_applicant = self.env['hr.applicant'].create({
            'name': 'Technical worker',
            'description': 'A nice applicant!',
            'job_id': self.job_dev.id,
            'source_id': self.richard_user.utm_source_id.id
        })

        self.assertEqual(job_applicant.ref_user_id, self.richard_user, "Referral is created with the right user")
        # self.assertEqual(job_applicant_2.ref_user_id, self.richard_user, "Referral is created with the right user")
        points_richard_c1 = self.env['hr.referral.points'].search([('ref_user_id', '=', self.richard_user.id), ('company_id', '=', self.company_1.id)])
        points_richard_c2 = self.env['hr.referral.points'].search([('ref_user_id', '=', self.richard_user.id), ('company_id', '=', self.company_2.id)])
        # All points are created for employee of company 1 as it's a job offer from company 1. No point in company 2.
        self.assertEqual(job_applicant.stage_id.points, sum(points_richard_c1.mapped('points')), "Right amount of referral points are created.")
        self.assertEqual(0, sum(points_richard_c2.mapped('points')), "Right amount of referral points are created.")

        # This user has no point in company 2 so if he miss as much points as the price of this object (this object is in company 2).
        self.assertEqual(self.red_mug_shop.points_missing, self.red_mug_shop.cost, "10 points are missing")

    def test_referral_no_hired_stage(self):
        self.env.ref('hr_recruitment.stage_job0').use_in_referral = False
        self.env.ref('hr_recruitment.stage_job3').use_in_referral = False
        stage_parking_1 = self.env['hr.recruitment.stage'].create({
            'name': 'parking1',
            'use_in_referral': False,
            'job_ids': [(6, 0, self.job_dev.ids)],
            'sequence': 15,
            'points': 500,  # points must be ignored for 'not hired stage'
        })
        stage_parking_2 = self.env['hr.recruitment.stage'].create({
            'name': 'parking2',
            'use_in_referral': False,
            'job_ids': [(6, 0, self.job_dev.ids)],
            'sequence': 16,
            'points': 1000,  # points must be ignored for 'not hired stage'
        })
        job_applicant = self.env['hr.applicant'].create({
            'name': 'Technical worker',
            'description': 'A nice applicant!',
            'job_id': self.job_dev.id,
            'ref_user_id': self.richard_user.id,
            'company_id': self.company_1.id,
            'stage_id': self.env.ref('hr_recruitment.stage_job1').id,
        })

        self.assertEqual(self.job_dev.max_points, 85, "Max points for this job is 85 (points for the 3 'not hired stage' are ignored).")
        self.assertEqual(job_applicant.earned_points, self.env.ref('hr_recruitment.stage_job1').points, "Richard received points corresponding to the first stage.")
        self.assertEqual(len(job_applicant.referral_points_ids), 1, "Richard received points corresponding to the first stage.")
        info_dashboard = json.loads(job_applicant.shared_item_infos)
        self.assertEqual(len(info_dashboard), 4, "In dashboard, we have only not 'not hired stage'.")
        self.assertEqual([x['done'] for x in info_dashboard], [True, False, False, False], "In dashboard, we have only not 'not hired stage' and state are correct.")

        job_applicant.stage_id = self.env.ref('hr_recruitment.stage_job3')
        self.assertEqual(job_applicant.earned_points, self.env.ref('hr_recruitment.stage_job1').points, "As he jump to a 'not hired stage', he receive no points and the jumped stages are ignored.")
        self.assertEqual(len(job_applicant.referral_points_ids), 1, "Richard received points corresponding to the first stage.")
        job_applicant.stage_id = self.env.ref('hr_recruitment.stage_job1')
        self.assertEqual(job_applicant.earned_points, self.env.ref('hr_recruitment.stage_job1').points, "As he jump from a 'not hired stage' to the stage where he was before the 'not hired stage', he receive no points.")
        self.assertEqual(len(job_applicant.referral_points_ids), 1, "Richard received points corresponding to the first stage.")

        job_applicant.stage_id = self.env.ref('hr_recruitment.stage_job3')
        self.assertEqual(job_applicant.earned_points, self.env.ref('hr_recruitment.stage_job1').points, "As he jump to a 'not hired stage', he receive no points and the jumped stages are ignored.")
        self.assertEqual(len(job_applicant.referral_points_ids), 1, "Richard received points corresponding to the first stage.")
        # We jump from not hired stage to another stage. All points between last valuable stage (stage 1) and new stage (stage 4) must be added
        job_applicant.stage_id = self.env.ref('hr_recruitment.stage_job4')
        self.assertEqual(job_applicant.earned_points, 35, "He received points for stage 2 and stage 4 (in addition to stage 1 that he already received).")
        self.assertEqual(len(job_applicant.referral_points_ids), 3, "3 lines in received points (2 new [for stage 2 and 4] and 1 old [for stage 1]).")
        info_dashboard = json.loads(job_applicant.shared_item_infos)
        self.assertEqual([x['done'] for x in info_dashboard], [True, True, True, False], "In dashboard, we have only not 'not hired stage' and state are correct.")

        # We jump between differents 'not hired stage' = > Nothing change
        job_applicant.stage_id = stage_parking_1
        job_applicant.stage_id = stage_parking_2
        job_applicant.stage_id = stage_parking_1
        job_applicant.stage_id = self.env.ref('hr_recruitment.stage_job3')
        job_applicant.stage_id = self.env.ref('hr_recruitment.stage_job4')  # We come back to previous not 'not hired stage'
        self.assertEqual(job_applicant.earned_points, 35, "Nothing change as it was only 'not hired stage'.")
        self.assertEqual(len(job_applicant.referral_points_ids), 3, "Nothing change as it was only 'not hired stage'.")

        # The applicant reach last not 'not hired stage'
        job_applicant.stage_id = self.env.ref('hr_recruitment.stage_job5')
        self.assertEqual(job_applicant.earned_points, 85, "He received all points.")
        self.assertEqual(len(job_applicant.referral_points_ids), 4, "We add a line in received points.")
        self.assertEqual(job_applicant.referral_state, 'hired', "Referral is hired, even if stage (not hired) exist with bigger sequence.")

    def test_referral_no_point_done_stage(self):
        """ Make sure stages use in referral with points = 0 are properly mark as done
        """
        final_stage = self.env.ref('hr_recruitment.stage_job5')
        # Change final sequence since we want new stage to be in between
        final_stage.sequence = 20
        stage_parking_1 = self.env['hr.recruitment.stage'].create({
            'name': 'parking1',
            'use_in_referral': True,
            'job_ids': [(6, 0, self.job_dev.ids)],
            'sequence': 15,
            'points': 0,
        })
        stage_parking_2 = self.env['hr.recruitment.stage'].create({
            'name': 'parking2',
            'use_in_referral': True,
            'job_ids': [(6, 0, self.job_dev.ids)],
            'sequence': 16,
            'points': 0,
        })
        job_applicant = self.env['hr.applicant'].create({
            'name': 'Technical worker',
            'description': 'A nice applicant!',
            'job_id': self.job_dev.id,
            'ref_user_id': self.richard_user.id,
            'company_id': self.company_1.id,
            'stage_id': self.env.ref('hr_recruitment.stage_job1').id,
        })

        info_dashboard = json.loads(job_applicant.shared_item_infos)
        self.assertEqual([x['done'] for x in info_dashboard], [True, True, False, False, False, False, False, False])
        job_applicant.stage_id = stage_parking_2
        info_dashboard = json.loads(job_applicant.shared_item_infos)
        self.assertEqual([x['done'] for x in info_dashboard], [True, True, True, True, True, True, True, False], "parking1 and parking2 should be marked as done")
        job_applicant.stage_id = stage_parking_1
        info_dashboard = json.loads(job_applicant.shared_item_infos)
        self.assertEqual([x['done'] for x in info_dashboard], [True, True, True, True, True, True, False, False], 'parking2 should not be marked as done anymore')
