# Part of Odoo. See LICENSE file for full copyright and licensing details.

from contextlib import contextmanager
from datetime import timedelta
from freezegun import freeze_time
from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.fields import Date, Markup
from odoo.tests.common import TransactionCase, tagged
from odoo.tools.zeep.exceptions import Fault

@tagged('-standard', 'external')
class TestMonsterIntegration(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.main_company = cls.env['res.company'].create({
            'name': 'My company',
            'hr_recruitment_monster_username': 'xrtpjobsx01',
            'hr_recruitment_monster_password': 'rtp987654'
        })

        cls.env = cls.env(context=dict(cls.env.context, allowed_company_ids=cls.main_company.ids))

        cls.partner = cls.env['res.partner'].create({
            'name': 'Odoo',
            'phone': '(603)-996-3829',
            'street': "rue des Bourlottes, 9",
            'street2': "",
            'city': "Ramillies",
            'zip': 1367,
            'state_id': False,
            'country_id': cls.env.ref('base.be').id,
        })

        cls.job1 = cls.env['hr.job'].create({
            'name': 'Test job 1',
            'address_id': cls.partner.id
        })

        cls.job2 = cls.env['hr.job'].create({
            'name': 'Test job 2',
            'address_id': cls.partner.id,
            'schedule_id': cls.env.ref('resource.resource_calendar_std').id
        })

        cls.monster_platform = cls.env['hr.recruitment.platform'].search([
            ('name', '=', 'Monster.com')
        ])

        cls.post_content = "As an employee of our company, you will collaborate with each department to create and deploy disruptive products. Come work at a growing company that offers great benefits with opportunities to moving forward and learn alongside accomplished leaders. We're seeking an experienced and outstanding member of staff. This position is both creative and rigorous by nature you need to think outside the box. We expect the candidate to be proactive and have a 'get it done' spirit."

        cls.today = Date().today()

    def create_publish_job_post(self, job_id, campaign_start_date, campaign_end_date=None):
        wiz_job_post = self.env['hr.recruitment.post.job.wizard'].create({
            'job_id': job_id,
            'job_apply_mail': 'example@test.com',
            'platform_ids': self.monster_platform.ids,
            'post_html': self.post_content,
            'campaign_start_date': campaign_start_date,
            'campaign_end_date': campaign_end_date,
        })
        wiz_job_post.action_post_job()
        return self.env['hr.job.post'].search(
            [],
            order='create_date desc',
            limit=1
        )

    def test_wrong_campaign_dates(self):
        yesterday = self.today - timedelta(days=1)
        with self.assertRaises(UserError):
            self.create_publish_job_post(self.job1.id, self.today, yesterday)

    def test_no_monster_credentials(self):
        self.main_company.hr_recruitment_monster_username = ''
        self.main_company.hr_recruitment_monster_password = ''

        job_post = self.create_publish_job_post(self.job1.id, self.today)

        if not job_post:
            self.fail("Should have created a job post.")
        self.assertEqual(job_post.status, 'failure')
        self.assertEqual(job_post.status_message, 'Monster.com credentials are not set. Please set them in the company settings or ask your administrator.')

        self.main_company.hr_recruitment_monster_username = 'xrtpjobsx01'
        self.main_company.hr_recruitment_monster_password = 'rtp987654'

    def test_wrong_credentials(self):
        self.main_company.hr_recruitment_monster_username = 'aaaaaaa'
        self.main_company.hr_recruitment_monster_password = 'aaaaaaa'

        job_post = self.create_publish_job_post(self.job1.id, self.today)

        if not job_post:
            self.fail("Should have created a job post.")
        self.assertEqual(job_post.status, 'failure')
        self.assertEqual(job_post.status_message, 'Authentication error: Monster.com credentials are invalid.')

        self.main_company.hr_recruitment_monster_username = 'xrtpjobsx01'
        self.main_company.hr_recruitment_monster_password = 'rtp987654'

    def test_create_post(self):
        job_post = self.create_publish_job_post(self.job1.id, self.today)
        if not job_post:
            self.fail("Should have created a job post.")
        self.assertEqual(job_post.job_id.id, self.job1.id)
        self.assertEqual(job_post.platform_id.id, self.monster_platform.id)
        self.assertEqual(job_post.campaign_start_date, self.today)
        self.assertEqual(job_post.post_html, Markup(f'<p>{self.post_content}</p>'))
        self.assertEqual(job_post.apply_vector, 'example@test.com')
        self.assertEqual(job_post.status, 'success')

    def test_create_post_with_job_having_schedule_id(self):
        job_post = self.create_publish_job_post(self.job2.id, self.today)
        if not job_post:
            self.fail("Should have created a job post.")
        self.assertEqual(job_post.job_id.id, self.job2.id)
        self.assertTrue(job_post.job_id.schedule_id)
        self.assertEqual(job_post.status, 'success')

    def test_delete_post(self):
        job_post = self.create_publish_job_post(self.job1.id, self.today)
        self.assertEqual(job_post.status, 'success')
        job_post._delete_post()
        self.assertEqual(job_post.status, 'deleted')

    @contextmanager
    def patch_post_api_call(self):
        def _post_api_call(data):
            if data['jobAction'] == 'delete':
                status = 'deleted'
            else:
                status = 'success'
            return {
                'status': status,
                'status_message': '',
            }

        with patch('odoo.addons.hr_recruitment_integration_monster.models.hr_recruitment_platform.RecruitmentPlatform._post_api_call') as patched_function:
            patched_function.side_effect = _post_api_call
            yield patched_function

    def test_postpone_create_post(self):
        tomorrow = self.today + timedelta(days=1)
        job_post = self.create_publish_job_post(self.job2.id, tomorrow)
        if not job_post:
            self.fail("Should have created a job post.")
        self.assertEqual(job_post.job_id.id, self.job2.id)
        self.assertEqual(job_post.platform_id.id, self.monster_platform.id)
        self.assertEqual(job_post.campaign_start_date, tomorrow)
        self.assertEqual(job_post.post_html, Markup(f'<p>{self.post_content}</p>'))
        self.assertEqual(job_post.apply_vector, 'example@test.com')
        self.assertEqual(job_post.status, 'pending')

        with freeze_time(self.today + timedelta(days=2)):
            # Patch API call as it complains with the freeze_time
            with self.patch_post_api_call():
                self.env.ref('hr_recruitment_integration_base.job_board_campaign_manager_start').method_direct_trigger()
                self.assertEqual(job_post.status, 'success')

    def test_postpone_already_posted(self):
        job_post = self.create_publish_job_post(self.job1.id, self.today)
        with self.assertRaises(UserError):
            job_post.campaign_start_date = self.today + timedelta(days=1)
            job_post.action_update_job_post()

    def test_stop_finished_campaign(self):
        tomorrow = self.today + timedelta(days=1)
        job_post = self.create_publish_job_post(self.job1.id, self.today, tomorrow)
        self.assertEqual(job_post.status, 'success')
        with freeze_time(self.today + timedelta(days=2)):
            # Patch API call as it complains with the freeze_time
            with self.patch_post_api_call():
                self.env.ref('hr_recruitment_integration_base.job_board_campaign_manager_stop').method_direct_trigger()
                self.assertEqual(job_post.status, 'deleted')


@tagged('standard', '-external')
class TestMockupMonsterIntegration(TestMonsterIntegration):

    @contextmanager
    def patch_monster_requests(self):
        """ Mock context for requests to the Monster.com API """

        class MockedClient:

            class Service:
                def __init__(self, username, password):
                    self.username = username
                    self.password = password

                def UpdateJobs(self, Job):
                    if self.username != "xrtpjobsx01" or self.password != "rtp987654":
                        raise Fault("Wrong credentials.")
                    if Job["jobAction"] == "addOrUpdate":
                        return {
                            "header":{
                                "header":"None"
                            },
                            "body":{
                                "ProcessingReceipt":{
                                    "RequestDocElement":"{http://schemas.monster.com/Monster}Jobs",
                                    "Status":{
                                        "ReturnCode":{
                                        "_value_1":"0",
                                        "returnCodeType":"success"
                                        },
                                        "Descriptions":"None"
                                    },
                                    "Response":"None"
                                },
                                "JobsPreProcessResponse":"None",
                                "JobResponse":[
                                    {
                                        "JobReference":{
                                        "JobTitle":"Test job 1",
                                        "JobRankingScore":"None",
                                        "jobRefCode":"110_20250114_1"
                                        },
                                        "RecruiterReference":{
                                        "UserName":"None",
                                        "PersonName":"None",
                                        "EmailAddress":"None",
                                        "userId":"204841377"
                                        },
                                        "FolderReference":{
                                        "FolderName":"Test job 1",
                                        "folderId":"338392218",
                                        "folderRefCode":"None"
                                        },
                                        "SubmissionReference":"None",
                                        "CompanyReference":{
                                        "CompanyXCode":"xrtpjobsx",
                                        "CompanyName":"None",
                                        "companyId":"34889333"
                                        },
                                        "JobPostingResponse":[
                                        {
                                            "InventoryPreference":"None",
                                            "RecruiterReference":"None",
                                            "Location":{
                                                "City":"None",
                                                "State":"Walloon-Brabant",
                                                "CountryCode":"BE",
                                                "PostalCode":"None",
                                                "Continent":"None",
                                                "locationId":795,
                                                "parentLocationId":"None"
                                            },
                                            "Locations":{
                                                "Location":[
                                                    {
                                                    "City":"None",
                                                    "State":"Walloon-Brabant",
                                                    "CountryCode":"BE",
                                                    "PostalCode":"None",
                                                    "Continent":"None",
                                                    "locationId":795,
                                                    "parentLocationId":"None"
                                                    }
                                                ]
                                            },
                                            "TargetLocationGroups":"None",
                                            "JobCategory":"None",
                                            "JobCategories":"None",
                                            "JobOccupations":"None",
                                            "JobCity":"None",
                                            "MoveJob":"None",
                                            "BoardName":{
                                                "_value_1":"None",
                                                "monsterId":"178",
                                                "boardGroupId":"None"
                                            },
                                            "JobPostingDates":{
                                                "JobPostDate":"None",
                                                "JobActiveDate":{
                                                    "_value_1":"Date().today()"
                                                },
                                                "JobExpireDate":{
                                                    "_value_1":"Date().today()"
                                                },
                                                "JobDeleteDate":"None",
                                                "JobModifiedDate":"None"
                                            },
                                            "CareerAdNetworkDates":"None",
                                            "PostingStats":"None",
                                            "ApplyOnlineURL":"None",
                                            "JobPostingSubBoards":"None",
                                            "PhysicalAddress":[
                                                
                                            ],
                                            "FilterParameters":"None",
                                            "DisplayTemplate":"None",
                                            "PositionOpenings":"None",
                                            "PostingOccupationalClassification":"None",
                                            "Industries":"None",
                                            "Video":"None",
                                            "JobTags":"None",
                                            "JobPostingProperties":"None",
                                            "JobViewURL":"None",
                                            "jobPostingAction":"None",
                                            "postingId":"284056346",
                                            "jobPostingRefCode":"None",
                                            "jobPostingState":"None",
                                            "bold":"None",
                                            "desiredDuration":"None"
                                        }
                                        ],
                                        "Status":{
                                        "ReturnCode":{
                                            "_value_1":"0",
                                            "returnCodeType":"success"
                                        },
                                        "Descriptions":{
                                            "Description":[
                                                {
                                                    "_value_1":"[PhysicalAddress/City] [Ramillies] is not valid City.Job will be posted with invalid city value for Physical Address. \r\n[PhysicalAddress/State] [False] is not valid state for Country [BE]. \r\nIndustry was not provided. \r\n",
                                                    "descriptionType":"warning"
                                                },
                                                {
                                                    "_value_1":"Job added. \r\n Charges: Job-Board(178) PLGId(0): 1; \r\n",
                                                    "descriptionType":"info"
                                                }
                                            ],
                                            "Errors":"None",
                                            "Warnings":"None",
                                            "Infos":"None"
                                        }
                                        },
                                        "JobCharges":{
                                        "JobCharge":[
                                            {
                                                "ResourceLicenseId":"349964004",
                                                "ChargeQuantity":"1",
                                                "postingId":"284056346"
                                            }
                                        ]
                                        }
                                    }
                                ],
                                "ProcessingSummary":"None",
                                "JobsPostProcessResponse":"None"
                            }}
                    elif Job["jobAction"] == "delete":
                        return {
                            "header":{
                                "header":"None"
                            },
                            "body":{
                                "ProcessingReceipt":{
                                    "RequestDocElement":"{http://schemas.monster.com/Monster}Jobs",
                                    "Status":{
                                        "ReturnCode":{
                                        "_value_1":"0",
                                        "returnCodeType":"success"
                                        },
                                        "Descriptions":"None"
                                    },
                                    "Response":"None"
                                },
                                "JobsPreProcessResponse":"None",
                                "JobResponse":[
                                    {
                                        "JobReference":{
                                        "JobTitle":"None",
                                        "JobRankingScore":"None",
                                        "jobRefCode":"110_20250114_1"
                                        },
                                        "RecruiterReference":{
                                        "UserName":"None",
                                        "PersonName":"None",
                                        "EmailAddress":"None",
                                        "userId":"204841377"
                                        },
                                        "FolderReference":{
                                        "FolderName":"None",
                                        "folderId":"0",
                                        "folderRefCode":"None"
                                        },
                                        "SubmissionReference":"None",
                                        "CompanyReference":{
                                        "CompanyXCode":"xrtpjobsx",
                                        "CompanyName":"None",
                                        "companyId":"34889333"
                                        },
                                        "JobPostingResponse":[
                                        
                                        ],
                                        "Status":{
                                        "ReturnCode":{
                                            "_value_1":"0",
                                            "returnCodeType":"success"
                                        },
                                        "Descriptions":{
                                            "Description":[
                                                {
                                                    "_value_1":"JobPosting [|284056346|178|795||] expired. \r\nCharges: 0 \r\n",
                                                    "descriptionType":"info"
                                                }
                                            ],
                                            "Errors":"None",
                                            "Warnings":"None",
                                            "Infos":"None"
                                        }
                                        },
                                        "JobCharges":"None"
                                    }
                                ],
                                "ProcessingSummary":"None",
                                "JobsPostProcessResponse":"None"
                            }}
                    return 

            def __init__(self, wsdl_uri, wsse):
                self.service = self.Service(wsse.username, wsse.password)
                self.wsdl_uri = wsdl_uri
                self.wsse = wsse

        with patch('odoo.addons.hr_recruitment_integration_monster.models.hr_recruitment_platform.Client') as mocked_client:
            mocked_client.side_effect = MockedClient
            yield mocked_client

    def test_wrong_campaign_dates(self):
        with self.patch_monster_requests():
            super().test_wrong_campaign_dates()

    def test_no_monster_credentials(self):
        with self.patch_monster_requests():
            super().test_no_monster_credentials()

    def test_wrong_credentials(self):
        with self.patch_monster_requests():
            super().test_wrong_credentials()
    
    def test_create_post(self):
        with self.patch_monster_requests():
            super().test_create_post()

    def test_delete_post(self):
        with self.patch_monster_requests():
            super().test_delete_post()

    def test_postpone_create_post(self):
        with self.patch_monster_requests():
            super().test_postpone_create_post()

    def test_postpone_already_posted(self):
        with self.patch_monster_requests():
            super().test_postpone_already_posted()

    def test_stop_finished_campaign(self):
        with self.patch_monster_requests():
            super().test_stop_finished_campaign()

    def test_create_post_with_job_having_schedule_id(self):
        with self.patch_monster_requests():
            super().test_create_post_with_job_having_schedule_id()
