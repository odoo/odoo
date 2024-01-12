# Part of Odoo. See LICENSE file for full copyright and licensing details.
from zeep import Client
from zeep.wsse.username import UsernameToken

from odoo import modules

# Test account provided by monster https://partner.monster.com/real-time-posting-devguide
# The resulting jobs in the testing environment can be checked
# here http://jobsearch.demo.monster.com
MONSTER_TEST_USERNAME_CREDENTIALS = "xrtpjobsx01"
MONSTER_TEST_PASSWORD_CREDENTIALS = "rtp987654"

class MonsterRequests(object):
    """ Low-level object intended to interface Odoo with Monster,
        through appropriate SOAP requests """

    def __init__(self, username=None, password=None, job_data=None, test_environment=False):
        self.test_environment = test_environment
        if test_environment:
            user_name_token = UsernameToken(MONSTER_TEST_USERNAME_CREDENTIALS,
                                            MONSTER_TEST_PASSWORD_CREDENTIALS)
        else:
            user_name_token = UsernameToken(username, password)
        wsdl_path = modules.get_module_path('hr_recruitment_integration_monster') + '/api/MonsterBusinessGateway.wsdl'
        self.client = Client('file:///%s' % wsdl_path,
                             wsse=user_name_token)
        self.data = job_data

    def post_job(self):
        self.data['jobAction'] = 'addOrUpdate'
        self.data['JobPostings']['JobPosting']['BoardName'] = {
            "monsterId": 178 if self.test_environment else 1
        }
        result = self.client.service.UpdateJobs(Job=self.data)
        return result

    def delete_job(self):
        self.data['jobAction'] = 'delete'
        self.data['JobPostings']['JobPosting']['BoardName'] = {
            "monsterId": 178 if self.test_environment else 1
        }
        result = self.client.service.UpdateJobs(Job=self.data)
        return result

    def set_job_title(self, job_title):
        self.data['JobInformation']['JobTitle'] = job_title

    def set_direct_apply(self, email):
        self.data['JobInformation']['ApplyType'] = {
             "monsterId": 1
        }

    def set_redirect_apply(self, url):
        self.data['JobInformation']['CustomApplyOnlineURL'] = url
