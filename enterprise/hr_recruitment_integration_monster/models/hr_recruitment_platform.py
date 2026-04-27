# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import models, _

from ..utils.zeep import Client
from odoo.tools.zeep.exceptions import Fault
from odoo.tools.zeep.wsse.username import UsernameToken

MONSTER_WSDL_URI = 'https://schemas.monster.com/Current/WSDL/MonsterBusinessGateway.wsdl'


class RecruitmentPlatform(models.Model):
    _inherit = 'hr.recruitment.platform'

    def _post_api_call(self, data):
        # To be overridden by the specific platform
        if self.id != self.env.ref('hr_recruitment_integration_monster.hr_recruitment_platform_monster').id:
            return super()._post_api_call(data)

        if not (username := self.env.company.sudo().hr_recruitment_monster_username)\
            or not (password := self.env.company.sudo().hr_recruitment_monster_password):
            return {
                'status': 'failure',
                'status_message': _(
                    'Monster.com credentials are not set. '
                    'Please set them in the company settings or ask your administrator.'
                ),
            }
        monster_soap_client = Client(
            MONSTER_WSDL_URI,
            wsse=UsernameToken(
                username=username,
                password=password,
            ),
        )

        for not_used in range(3):
            # service can be down for a short time
            try:
                monster_response = monster_soap_client.service.UpdateJobs(Job=data)
            except TimeoutError:
                continue
            except (KeyError, ValueError):
                return {
                    'status': 'failure',
                    'status_message': _(
                        'Critical error: Monster.com service has changed. '
                        'Please contact customer support.'
                    ),
                }
            except Fault:
                return {
                    'status': 'failure',
                    'status_message': _(
                        'Authentication error: Monster.com credentials are invalid.'
                    ),
                }
            else:
                break
        else:
            # service is down for an unreasonable amount of time
            return {
                'status': 'failure',
                'status_message':  _(
                    'Service not available: Monster.com service is not available. '
                    'Please try again later.'
                ),
            }

        if data['jobAction'] == 'delete':
            status = 'deleted'
        else:
            status = 'success'

        message_dict = defaultdict(list)
        # This logic doesn't take into account the possibility of job variants
        for job_response in monster_response['body']['JobResponse']:
            if job_response['Status']['ReturnCode']['_value_1'] != '0' and status != 'expired':
                status = 'failure'

            for log_dict in job_response['Status']['Descriptions']['Description']:
                message_dict[log_dict['descriptionType']].append(log_dict['_value_1'])
                if 'no active Job with JobRefCode' in log_dict['_value_1']:
                    status = 'expired'

        message = '\n'.join([
            f'{error_level}: {message}'
            for error_level, message_list in message_dict.items()
            for message in message_list
        ])

        return {
            'status': status,
            'status_message': message,
        }
