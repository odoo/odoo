# Part of Odoo. See LICENSE file for full copyright and licensing details.

from contextlib import contextmanager
from unittest.mock import patch

from odoo.exceptions import RedirectWarning, UserError
from odoo.fields import Date, Markup
from odoo.tests.common import TransactionCase, tagged
from odoo.tools.zeep.exceptions import Fault

@tagged('-standard', 'external')
class TestWebsiteMonsterIntegration(TransactionCase):

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
            'address_id': cls.partner.id,
            'website_description': 'This is a very cool job, you will like it!',
            'is_published': True
        })

        cls.job2 = cls.env['hr.job'].create({
            'name': 'Test job 2',
            'address_id': cls.partner.id,
            'is_published': False
        })

        cls.monster_platform = cls.env['hr.recruitment.platform'].search([
            ('name', '=', 'Monster.com')
        ])

        cls.post_content = "As an employee of our company, you will collaborate with each department to create and deploy disruptive products. Come work at a growing company that offers great benefits with opportunities to moving forward and learn alongside accomplished leaders. We're seeking an experienced and outstanding member of staff. This position is both creative and rigorous by nature you need to think outside the box. We expect the candidate to be proactive and have a 'get it done' spirit."

        cls.today = Date().today()
    
    def test_create_post_no_platform(self):
        wiz_job_post = self.env['hr.recruitment.post.job.wizard'].with_context({'active_model': 'hr.job', 'active_id': self.job1.id}).create({
            'job_id': self.job1.id,
            'apply_method': 'email',
            'job_apply_mail': 'example@test.com',
            'post_html': 'This is my job description',
            'campaign_start_date': self.today,
        })
        with self.assertRaises(UserError):
            wiz_job_post.action_post_job()
    
    def test_create_post_no_apply_url(self):
        wiz_job_post = self.env['hr.recruitment.post.job.wizard'].with_context({'active_model': 'hr.job', 'active_id': self.job1.id}).create({
            'job_id': self.job1.id,
            'apply_method': 'redirect',
            'job_apply_url': False,
            'platform_ids': self.monster_platform.ids,
            'post_html': 'This is my job description',
            'campaign_start_date': self.today,
        })
        with self.assertRaises(UserError):
            wiz_job_post.action_post_job()

    def test_create_post_no_published(self):
        wiz_job_post = self.env['hr.recruitment.post.job.wizard'].with_context({'active_model': 'hr.job', 'active_id': self.job2.id}).create({
            'job_id': self.job2.id,
            'platform_ids': self.monster_platform.ids,
            'apply_method': 'redirect',
            'job_apply_url': 'https://odoo.com',
            'post_html': 'This is my job description',
            'campaign_start_date': self.today,
        })
        with self.assertRaises(UserError):
            wiz_job_post.action_post_job()

    def test_create_post_no_post_html(self):
        wiz_job_post = self.env['hr.recruitment.post.job.wizard'].with_context({'active_model': 'hr.job', 'active_id': self.job2.id}).create({
            'job_id': self.job2.id,
            'platform_ids': self.monster_platform.ids,
            'apply_method': 'redirect',
            'job_apply_url': 'https://odoo.com',
            'post_html': False,
            'campaign_start_date': self.today,
        })
        with self.assertRaises(UserError):
            wiz_job_post.action_post_job()

    def test_create_post_no_campaing_start_date(self):
        wiz_job_post = self.env['hr.recruitment.post.job.wizard'].with_context({'active_model': 'hr.job', 'active_id': self.job2.id}).create({
            'job_id': self.job2.id,
            'platform_ids': self.monster_platform.ids,
            'apply_method': 'redirect',
            'job_apply_url': 'https://odoo.com',
            'post_html': 'This is my job description',
            'campaign_start_date': False,
        })
        with self.assertRaises(UserError):
            wiz_job_post.action_post_job()

    def test_default_apply_url(self):
        wiz_job_post = self.env['hr.recruitment.post.job.wizard'].with_context({'active_model': 'hr.job', 'active_id': self.job1.id}).create({
            'job_id': self.job1.id,
            'platform_ids': self.monster_platform.ids,
            'apply_method': 'redirect',
            'post_html': 'This is my job description',
            'campaign_start_date': self.today,
        })
        wiz_job_post.action_post_job()
        self.assertEqual(wiz_job_post.job_apply_url, self.job1.full_url)

    def test_default_post_html(self):
        wiz_job_post = self.env['hr.recruitment.post.job.wizard'].with_context({'active_model': 'hr.job', 'active_id': self.job1.id}).create({
            'job_id': self.job1.id,
            'platform_ids': self.monster_platform.ids,
            'apply_method': 'redirect',
            'campaign_start_date': self.today,
        })
        wiz_job_post.action_post_job()
        self.assertEqual(wiz_job_post.post_html, Markup(f"<p>{self.job1.website_description}</p>"))

    def test_generate_post_warning(self):
        wiz_job_post = self.env['hr.recruitment.post.job.wizard'].with_context({'active_model': 'hr.job', 'active_id': self.job1.id}).create({
            'job_id': self.job1.id,
            'platform_ids': self.monster_platform.ids,
            'apply_method': 'redirect',
            'post_html': 'This is my job description',
            'campaign_start_date': self.today,
        })
        with self.assertRaises(RedirectWarning):
            wiz_job_post.action_generate_post()

    def test_generate_post_not_published(self):
        wiz_job_post = self.env['hr.recruitment.post.job.wizard'].with_context({'active_model': 'hr.job', 'active_id': self.job2.id}).create({
            'job_id': self.job2.id,
            'platform_ids': self.monster_platform.ids,
            'apply_method': 'redirect',
            'post_html': 'This is my job description',
            'campaign_start_date': self.today,
        })
        with self.assertRaises(UserError):
            wiz_job_post.action_generate_post(warning=False)


@tagged('standard', '-external')
class TestMockupWebsiteMonsterIntegration(TestWebsiteMonsterIntegration):

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
                    return 

            def __init__(self, wsdl_uri, wsse):
                self.service = self.Service(wsse.username, wsse.password)
                self.wsdl_uri = wsdl_uri
                self.wsse = wsse

        with patch('odoo.addons.hr_recruitment_integration_monster.models.hr_recruitment_platform.Client') as mocked_client:
            mocked_client.side_effect = MockedClient
            yield mocked_client

    def test_create_post_no_platform(self):
        with self.patch_monster_requests():
            super().test_create_post_no_platform()

    def test_create_post_no_apply_url(self):
        with self.patch_monster_requests():
            super().test_create_post_no_apply_url()

    def test_create_post_no_published(self):
        with self.patch_monster_requests():
            super().test_create_post_no_published()
    
    def test_create_post_no_post_html(self):
        with self.patch_monster_requests():
            super().test_create_post_no_post_html()

    def test_create_post_no_campaing_start_date(self):
        with self.patch_monster_requests():
            super().test_create_post_no_campaing_start_date()

    def test_default_apply_url(self):
        with self.patch_monster_requests():
            super().test_default_apply_url()

    def test_default_post_html(self):
        with self.patch_monster_requests():
            super().test_default_post_html()

    def test_generate_post_warning(self):
        with self.patch_monster_requests():
            super().test_generate_post_warning()

    def test_generate_post_not_published(self):
        with self.patch_monster_requests():
            super().test_generate_post_not_published()

