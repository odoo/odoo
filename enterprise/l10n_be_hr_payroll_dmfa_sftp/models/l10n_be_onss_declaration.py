# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import logging

from io import BytesIO

from odoo.addons.l10n_be_hr_payroll_dmfa_sftp.models.utils import xml_str_to_dict, open_sftp_connection
from odoo.exceptions import UserError
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class L10nBeOnssDeclaration(models.Model):
    _name = 'l10n.be.onss.declaration'
    _description = 'ONSS Declaration'

    name = fields.Char(compute='_compute_name', store=True)
    dmfa_id = fields.Many2one('l10n_be.dmfa', required=True)
    company_id = fields.Many2one('res.company', related="dmfa_id.company_id", store=True)
    environment = fields.Selection(
        selection=[
            ('R', 'Production'),
            ('T', 'Circuit Test'),
            ('S', 'Declaration Test'),
        ],
        required=True)
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('posted', 'Posted'),
            ('received', 'Received'),
            ('notified', 'Notified'),
            ('error', 'Error'),
            ('other', 'Other'),
        ],
        required=True,
        default='draft')
    onss_file_ids = fields.One2many('l10n.be.onss.file', 'onss_declaration_id')
    onss_file_count = fields.Integer(compute='_compute_onss_file_count')
    error_message = fields.Text()

    @api.depends('dmfa_id')
    def _compute_name(self):
        for declaration in self:
            declaration.name = f"{declaration.id}: {declaration.dmfa_id.name}"

    @api.depends('onss_file_ids')
    def _compute_onss_file_count(self):
        for declaration in self:
            declaration.onss_file_count = len(declaration.onss_file_ids)

    def action_open_onss_file(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id('l10n_be_hr_payroll_dmfa_sftp.action_l10n_be_onss_file')
        action.update({
            'domain': [('onss_declaration_id', '=', self.id)],
        })
        return action

    @api.model
    def _check_access_sftp_connection(self):
        self.check_access('read')  # we use sudo below, double-check permissions early
        _logger.info("User %s starting ONSS SFTP connection for company %s",
                     self.env.user.login, self.env.company.name)

    @api.model
    def action_test_sftp_connection(self):
        self.ensure_one()
        self._check_access_sftp_connection()
        with open_sftp_connection(self.env.company.sudo().onss_sftp_private_key, self.env.company.sudo().onss_technical_user_name) as sftp:
            # List files in home directory
            files = sftp.listdir('.')
            success_msg = _("Connection Test Succeeded. Files in remote root: %s", files)
            _logger.info(success_msg)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': success_msg,
                'next': {
                    'type': 'ir.actions.client',
                    'tag': 'soft_reload',
                },
            }
        }

    def action_post(self):
        self.ensure_one()
        self._check_access_sftp_connection()
        with open_sftp_connection(self.env.company.sudo().onss_sftp_private_key, self.env.company.sudo().onss_technical_user_name) as sftp:
            if self.environment == "R":
                target_folder = "IN"
            elif self.environment == "T":
                target_folder = "INTEST"
            else:
                target_folder = "INTEST-S"

            for file in self.onss_file_ids:
                # Considered safe by construction, and will be rejected by ONSS server
                # if format / location is invalid
                remote_path = f'/{target_folder}/{file.name}'

                file_data = base64.b64decode(file.file)

                file_stream = BytesIO(file_data)
                sftp.putfo(file_stream, remote_path)
                _logger.info("File %s uploaded to %s", file.name, remote_path)

        self.state = 'posted'
        self.dmfa_id.message_post(body=_(
            'The %(declaration)s (id=%(declaration_id)s) has been posted by %(user)s to ONSS portal',
            declaration=self._get_html_link(_('declaration')),
            declaration_id=self.id,
            user=self.env.user.name))

        success_msg = _("Declaration posted successfully to %(folder)s", folder=target_folder)
        _logger.info(success_msg)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': success_msg,
                'next': {
                    'type': 'ir.actions.client',
                    'tag': 'soft_reload',
                },
            }
        }

    @api.model
    def _analyse_acrf_file(self, data_dict):
        reference_name = data_dict['ACRF']['Form']['FileReference']['FileName']
        onss_declaration = self.env['l10n.be.onss.file'].search(
            [('name', '=', reference_name)], limit=1
        ).onss_declaration_id
        if not onss_declaration:
            return onss_declaration
        reception_result = data_dict['ACRF']['Form']['ReceptionResult']
        if reception_result['ResultCode'] == '0':
            onss_declaration.state = 'error'
            error_code = reception_result['ErrorID']
            onss_declaration.error_message = f"{error_code}\n{self._get_error_label(error_code.split('-')[-1])}"
            onss_declaration.dmfa_id.message_post(body=_(
                'The %(declaration)s (id=%(declaration_id)s) has been received as invalid by the ONSS',
                declaration=onss_declaration._get_html_link(_('declaration')),
                declaration_id=onss_declaration.id))
        else:
            onss_declaration.dmfa_id.message_post(body=_(
                'The %(declaration)s (id=%(declaration_id)s) has been received as valid by the ONSS',
                declaration=onss_declaration._get_html_link(_('declaration')),
                declaration_id=onss_declaration.id))
            onss_declaration.state = 'received'
        return onss_declaration

    @api.model
    def _analyse_notification_file(self, data_dict):
        form = data_dict['NOTIFICATION']['Form']
        notification_type = form['HandledOriginalForm']['Identification']
        onss_declaration = self.env['l10n.be.onss.declaration']
        employee = self.env['hr.employee']
        if notification_type == "DMFA":
            if 'FileReference' in form:
                reference_name = form['FileReference']['FileName']
                onss_declaration = self.env['l10n.be.onss.file'].search(
                    [('name', '=', reference_name)], limit=1
                ).onss_declaration_id
            else:
                onss_declaration = self.env['l10n.be.onss.file'].search([
                    ('form_creation_date', '=', form['HandledOriginalForm']['FormCreationDate']),
                    ('form_creation_hour', '=', form['HandledOriginalForm']['FormCreationHour']),
                ], limit=1).onss_declaration_id
            if not onss_declaration:
                return onss_declaration, employee
            reception_result = form['HandlingResult']
            error_message = []
            if reception_result['ResultCode'] in ['0', '2', '3']:
                onss_declaration.state = 'error'
                onss_declaration.dmfa_id.message_post(body=_(
                    'The %(declaration)s (id=%(declaration_id)s) has been notified as invalid by the ONSS',
                    declaration=onss_declaration._get_html_link(_('declaration')),
                    declaration_id=onss_declaration.id))
                diagnosis_code = reception_result.get('Diagnosis', '3')
                error_message.append(self._get_diagnosis_label(diagnosis_code))
            else:
                onss_declaration.state = 'notified'
                onss_declaration.dmfa_id.message_post(body=_(
                    'The %(declaration)s (id=%(declaration_id)s) has been notified as valid by the ONSS',
                    declaration=onss_declaration._get_html_link(_('declaration')),
                    declaration_id=onss_declaration.id))
            anomalies = reception_result.get('AnomalyReport', {})
            if isinstance(anomalies, dict):
                anomalies = [anomalies]
            anomalies_count = len(anomalies)
            count = 0
            employee_by_niss = {}
            for anomaly in anomalies:
                count += 1
                error_code = anomaly['ErrorID']
                error_message += [
                    _("Anomaly (%(count)s/%(total)s) - Code: %(error_code)s", count=count, total=anomalies_count, error_code=error_code),
                    self._get_error_label(error_code.split('-')[-1]),
                ]
                if 'TagName' in anomaly:
                    error_message.append(_('- Tag Name: %s', anomaly['TagName']))
                if 'Value' in anomaly:
                    error_message.append(_('- Value: %s', anomaly['Value']))
                niss = anomaly.get('Path', {}).get('INSS', False)
                if niss:
                    if niss in employee_by_niss:
                        employee = employee_by_niss[niss]
                    else:
                        employee = self.env['hr.employee'].with_context(active_test=False).search([('niss', '=', niss)], limit=1)
                        employee_by_niss[niss] = employee
                    if employee:
                        error_message.append(_('- Employee: %(employee_name)s (NISS: %(niss)s)', employee_name=employee.name, niss=niss))
                    else:
                        error_message.append(_('- NISS: %s', niss))
                else:
                    error_message.append(_('- NISS: %s', niss))
                if 'SystemCorrection' in anomaly:
                    block_action = anomaly['SystemCorrection']['BlockAction']
                    block_action_lines = [
                        _("=== System Correction ==="),
                        _("Correction Type   : %s", anomaly['SystemCorrection']['CorrectionType']),
                        _("Action            : %s", block_action.get('Action', _('N/A'))),
                        _("Block Name        : %s", block_action.get('BlockName', _('N/A'))),
                        _("Field to Correct  : %s", block_action['DataValue'].get('FieldName', _('N/A'))),
                        _("Corrected Value   : %s", block_action['DataValue'].get('NewValue', _('N/A'))),
                        _("--- Related Info ---"),
                    ]
                    for key, value in block_action.items():
                        if key in ['DataValue', 'Action', 'BlockName']:
                            continue
                        block_action_lines.append(f"{key}: {value}")
                    error_message += block_action_lines

                error_message += [
                    _('- Anomaly Class: %s', self._get_anomaly_class_label(anomaly.get('AnomalyClass'))),
                    '\n',
                ]
            onss_declaration.error_message = '\n'.join(error_message)
        elif notification_type == "DIMONA":
            if 'NaturalPerson' in form and 'INSS' in form['NaturalPerson']:
                employee_data = form['NaturalPerson']
                employee = self.env['hr.employee'].with_context(active_test=False).search([('niss', '=', employee_data['INSS'])], limit=1)
                if employee:
                    error_message = []
                    if form['HandlingResult'].get('ResultCode') in ['0', '2', '3']:
                        anomaly = form['HandlingResult']['AnomalyReport']
                        error_code = anomaly['ErrorID']
                        error_message += [
                            error_code,
                            self._get_error_label(error_code.split('-')[-1]),
                            _('- Anomaly Class: %s', self._get_anomaly_class_label(anomaly.get('AnomalyClass'))),
                            '\n',
                        ]
                        employee.message_post(body=_(
                            'The DIMONA declaration has been notified as invalid by the ONSS:\n%(error_message)s',
                            error_message='\n'.join(error_message)))
                    else:
                        dimona_data = form['HandlingResult']['ImpactReport']['DimonaImpactReport']['DimonaPeriodAfter']
                        employee.message_post(
                            body=_(
                                "DIMONA declaration opened (Starting %(start)s, Ending %(end)s)",
                                start=dimona_data.get('StartingDate', _('Unknown')),
                                end=dimona_data.get('EndingDate', _('Unknown'))
                            ))
            elif 'ApplicationData' in form:
                application_form = form['ApplicationData']['Form']
                for dimona_type in ['DimonaIn', 'DimonaOut', 'DimonaUpdate', 'DimonaCancel']:
                    if dimona_type in application_form and 'INSS' in application_form[dimona_type]['NaturalPerson']:
                        employee_data = application_form[dimona_type]['NaturalPerson']
                        employee = self.env['hr.employee'].with_context(active_test=False).search([('niss', '=', employee_data['INSS'])], limit=1)
                        if employee:
                            employee.message_post(
                                body=_(
                                    "DIMONA declaration done (Starting %(start)s, Ending %(end)s)",
                                    start=application_form[dimona_type].get('StartingDate', _('Unknown')),
                                    end=application_form[dimona_type].get('EndingDate', _('Unknown'))
                                ))
        return onss_declaration, employee

    @api.model
    def _analyse_idflux_file(self, data_dict):
        form = data_dict['IDFLUX']['Form']
        onss_declaration = self.env['l10n.be.onss.declaration']
        employee = self.env['hr.employee']
        # NISS Mutation
        old_niss = form.get('IdfluxInformation', {}).get('OutdatedSituation', {}).get('INSS', False)
        valid_niss = form.get('IdfluxInformation', {}).get('ValidSituation', {}).get('INSS', False)
        if old_niss:
            employee = self.env['hr.employee'].with_context(active_test=False).search([('niss', '=', old_niss)], limit=1)
            employee.niss = valid_niss
            if employee:
                employee.message_post(
                    body=_(
                        "DIMONA NISS Mutation declaration (old: %(old_niss)s, new %(new_niss)s)",
                        old_niss=old_niss,
                        new_niss=valid_niss,
                    ))
        else:
            employee = self.env['hr.employee'].with_context(active_test=False).search([('niss', '=', valid_niss)], limit=1)
        return onss_declaration, employee

    @api.model
    def _fetch_files(self):
        self._check_access_sftp_connection()
        with open_sftp_connection(self.env.company.sudo().onss_sftp_private_key, self.env.company.sudo().onss_technical_user_name) as sftp:
            target_folders = ['OUT', 'OUTTEST', 'OUTTEST-S']
            onss_file_vals = []

            for folder in target_folders:
                try:
                    file_names = sftp.listdir(folder)
                    _logger.info(_("Found %(count)s files in %(folder)s", count=len(file_names), folder=folder))
                except FileNotFoundError:
                    error_msg = _("Directory not found on server: %s", folder)
                    _logger.warning(error_msg)
                    raise UserError(error_msg)
                except Exception as e:  # noqa: BLE001
                    error_msg = _("Error reading files from %(folder)s: %(error)s", folder=folder, error=e)
                    _logger.error(error_msg)
                    raise UserError(error_msg)

                all_onss_filenames = self.env['l10n.be.onss.file'].search_fetch([('name', 'in', file_names)], ['name']).mapped('name')
                for filename in file_names:
                    if filename in all_onss_filenames:
                        continue
                    remote_path = f"{folder}/{filename}"
                    with sftp.file(remote_path, mode='rb') as remote_file:
                        content = remote_file.read()
                        onss_declaration = self.env['l10n.be.onss.declaration']
                        employee = self.env['hr.employee']
                        data_dict = {}
                        try:
                            # Determine ONSS Declaration
                            xml_str = content.decode()
                            data_dict = xml_str_to_dict(xml_str)
                        except Exception as e:  # noqa: BLE001
                            _logger.info("Unabled to deduct ONSS declaration for non xml file %s: %s", filename, e)
                            pass
                        if 'ACRF' in data_dict:
                            onss_declaration = self._analyse_acrf_file(data_dict)
                        elif 'NOTIFICATION' in data_dict:
                            onss_declaration, employee = self._analyse_notification_file(data_dict)
                        elif 'IDFLUX' in data_dict:
                            onss_declaration, employee = self._analyse_idflux_file(data_dict)

                        onss_file_vals.append({
                            'name': filename,
                            'file': base64.b64encode(content).decode('utf-8'),
                            'onss_declaration_id': onss_declaration.id,
                            'employee_id': employee.id,
                        })
        onss_files = self.env['l10n.be.onss.file'].create(onss_file_vals)
        for onss_file in onss_files:
            if onss_file.onss_declaration_id:
                continue
            matching_file = self.env['l10n.be.onss.file'].search([
                ('name', 'like', '.'.join(onss_file.name.split('.')[1:])),
                ('onss_declaration_id', '!=', False),
            ], limit=1)
            onss_file.onss_declaration_id = matching_file.onss_declaration_id
        success_msg = _("ONSS Files fetched successfully (%s new imported files)", len(onss_files))
        _logger.info(success_msg)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': success_msg,
                'next': {
                    'type': 'ir.actions.client',
                    'tag': 'soft_reload',
                },
            },
        }

    @api.model
    def _get_error_label(self, code):
        error_messages = {
            '001': self.env._('Not present'),
            '002': self.env._('Non-numeric'),
            '003': self.env._('Invalid'),
            '004': self.env._('Invalid control number'),
            '005': self.env._('Prohibited'),
            '006': self.env._('Too many occurrences with the same identifiers'),
            '007': self.env._('Calculated total different from declared total'),
            '008': self.env._('Not within scope'),
            '009': self.env._('Age to verify'),
            '010': self.env._('Other deduction requested'),
            '011': self.env._('Negative balance by employer category'),
            '012': self.env._('Total to verify'),
            '013': self.env._('Total too high'),
            '014': self.env._('End date before the start date'),
            '015': self.env._('Agreement date later than the start date of employment'),
            '016': self.env._('Employer not affiliated with an approved social security office'),
            '017': self.env._('Employer not included in the directory'),
            '018': self.env._('Calculation error (fixed rates)'),
            '019': self.env._('Incompatibility with the year of the reference period start date'),
            '020': self.env._('Incompatibility with the joint committee'),
            '021': self.env._('Incompatibility with the declared period'),
            '022': self.env._('Incompatibility with the directory'),
            '023': self.env._('Incompatibility with the risk'),
            '024': self.env._('Incompatibility with a natural person'),
            '025': self.env._('Incompatibility with employer category'),
            '026': self.env._('Incompatibility with code FFE'),
            '027': self.env._('Importance code mismatch'),
            '028': self.env._('NACE code mismatch'),
            '029': self.env._('Remuneration code mismatch'),
            '030': self.env._('Worker code mismatch'),
            '031': self.env._('Name and NISS mismatch'),
            '032': self.env._('Work schedule mismatch'),
            '033': self.env._('SIS and NISS mismatch'),
            '034': self.env._('Quarter mismatch'),
            '035': self.env._('Quarter - employer category mismatch'),
            '036': self.env._('Incompatible with employee number'),
            '037': self.env._('The year does not match the year of the accident'),
            '038': self.env._('The Isabel signature is incorrect'),
            '039': self.env._('The Isabel user is not authorized to send in real time'),
            '040': self.env._('The time (hours/minutes) of the activity is before the time of the accident, even though the activity and the accident occurred at the same time'),
            '041': self.env._('Incorrect ONSS/PPL number'),
            '042': self.env._('Fewer than 50 workers'),
            '043': self.env._('Amount to be verified'),
            '044': self.env._('Calculated amount different from the declared amount'),
            '045': self.env._('Amount too high'),
            '046': self.env._('Amount too low'),
            '047': self.env._('Number too high'),
            '048': self.env._('Not present - intermittent worker'),
            '049': self.env._('Not present - seasonal worker'),
            '050': self.env._('Not planned for this employer'),
            '051': self.env._('Not included in the directory for the reporting quarter'),
            '052': self.env._('Response to request already returned'),
            '053': self.env._('Not applicable'),
            '054': self.env._('Not entitled'),
            '055': self.env._('Not SME'),
            '056': self.env._('First sequence number other than 1'),
            '057': self.env._('Benefits to be verified'),
            '058': self.env._('Insufficient benefits'),
            '059': self.env._('Non-linear progression of sequence number'),
            '060': self.env._('Worker too old'),
            '061': self.env._('Worker too young'),
            '062': self.env._('Zone not applicable'),
            '063': self.env._('Time unit incompatibility'),
            '064': self.env._('Deduction not applicable for this level'),
            '065': self.env._('Multiple deduction detail blocks present'),
            '066': self.env._('No deduction detail block present'),
            '067': self.env._('Employment promotion measure cannot be indicated'),
            '068': self.env._('Incorrect employment promotion measure'),
            '069': self.env._('Incorrect working time reorganization measure'),
            '070': self.env._('NISS unknown to the authentic source'),
            '071': self.env._('Difference between employer and authentic source'),
            '072': self.env._('Difference between ONSS validity period and authentic source'),
            '073': self.env._('Difference between ONSS deduction type and authentic source'),
            '074': self.env._('Quarter not authorized for employer'),
            '075': self.env._('Not authorized for apprentice type'),
            '076': self.env._('Percentage of benefits (µ) does not meet requirements'),
            '077': self.env._('Worker does not meet age requirements'),
            '078': self.env._('Reporting quarter not included in the validity period'),
            '079': self.env._('Worker not in service on the last day of the quarter'),
            '080': self.env._('Working schedule does not meet requirements'),
            '082': self.env._('Block not applicable'),
            '083': self.env._('Working time reduction too low'),
            '084': self.env._('Quarter - category - worker contribution code incompatibility'),
            '085': self.env._('Employer category / worker code incompatibility'),
            '088': self.env._('Unknown schedule'),
            '089': self.env._('Unknown root'),
            '090': self.env._('Error in cardinality'),
            '091': self.env._('Sequence error'),
            '092': self.env._('Unknown element'),
            '093': self.env._('Incorrect length'),
            '094': self.env._('Worker type incompatibility'),
            '095': self.env._('Total number of days incompatible with the reporting quarter for the occupation'),
            '096': self.env._('Total number of days incompatible with the work schedule for the occupation'),
            '097': self.env._('Reference period incompatibility'),
            '098': self.env._('Start date incompatibility'),
            '099': self.env._('Occupation incompatibility'),
            '100': self.env._('Total number of hours for the day indication exceeds the scope of definition'),
            '101': self.env._('Sender not authorized for this employee number'),
            '102': self.env._('Incorrect XML syntax'),
            '103': self.env._('Sender not authorized'),
            '104': self.env._('Incompatibility between benefits and remuneration'),
            '105': self.env._('Occupation after the current quarter'),
            '107': self.env._('The structure of a GO file name is incorrect'),
            '108': self.env._("The sender specified in the file name or the RFH2 of the MQ-series message does not match the sender listed in the directory name where the file was uploaded or the user ID specified in the MQMD of said message."),
            '109': self.env._('The date specified in the file name or the RFH2 has more or less 8 digits.'),
            '110': self.env._('The date specified in the file name or RFH2 is not a valid date in YYYYMMDD format'),
            '111': self.env._("The date specified in the file name or RFH2 is greater than today's date"),
            '112': self.env._('The item number specified in the file name or RFH2 has more or less than 5 digits'),
            '113': self.env._('The item number specified in the file name or RFH2 is not numeric'),
            '114': self.env._('The number of pieces specified in the file name has more or less than 1 digit'),
            '115': self.env._('The number of pieces specified in the file name is not numeric'),
            '116': self.env._('The number of pieces specified in the file name is zero'),
            '117': self.env._('The environment specified in the file name or RFH2 is different from T, R, and S'),
            '118': self.env._('A file or message with an R environment was deposited in a directory other than IN or in a queue not reserved for production, respectively;'),
            '119': self.env._('A file or message with an T environment was deposited in a directory other than INTEST or in a queue not reserved for testing, respectively.'),
            '120': self.env._('The number of FI files in the directory does not match the number of required files'),
            '121': self.env._('No signature file must be provided for the communication protocol used'),
            '122': self.env._('The number of FS files in the directory does not match the number of required files'),
            '123': self.env._('Incorrect numbering for FI files'),
            '124': self.env._('Incorrect numbering for files FS'),
            '125': self.env._('Invalid signature'),
            '126': self.env._("The date specified in the file name or RFH2 is too old compared to today's date."),
            '127': self.env._('The upload number specified in the file name or RFH2 is zero'),
            '128': self.env._('The number of pieces specified in the file name is greater than the maximum allowed'),
            '129': self.env._('Incorrect file name prefix or Identification tag value in RFH2'),
            '130': self.env._('GO file not received for a set of files'),
            '131': self.env._('The name structure of an FI file or RFH2 is incorrect'),
            '132': self.env._('The name structure of an FS file is incorrect'),
            '133': self.env._('A file with the same name has already been sent previously. A message with the same RFH2 has already been sent previously.'),
            '134': self.env._('No data'),
            '135': self.env._('Inconsistency between the specified form type and the schema'),
            '136': self.env._('No schema was specified'),
            '137': self.env._('The specified schema standard is not supported or is unknown'),
            '138': self.env._('The specified encoding is not supported'),
            '139': self.env._('The document does not have a default NameSpace or the default NameSpace is not compliant'),
            '140': self.env._("The mailbox_id in the incoming file does not match its mailbox_id in the sender's database"),
            '141': self.env._('The Isabel signature hash is not correct'),
            '142': self.env._('No declaration file attached'),
            '143': self.env._('Isabel reports that the message was duplicated'),
            '144': self.env._('The work environment could not be detected in the message name'),
            '145': self.env._('Occupation after the quarter covered by the data'),
            '146': self.env._('Not allowed'),
            '147': self.env._('Duplicate work schedule'),
            '148': self.env._('The day is not indicated'),
            '149': self.env._('The beneficiary is not indicated'),
            '150': self.env._('Incompatibility between the month of the first day of youth or senior vacation'),
            '151': self.env._('Not identifiable'),
            '152': self.env._('No employment relationship found for the given period or date'),
            '153': self.env._('Incompatibility between the certificate and its owner'),
            '154': self.env._('Incompatibility between the sender number and the file purpose'),
            '155': self.env._('No or no longer a mandate'),
            '156': self.env._('Technical problem receiving ISABEL'),
            '157': self.env._('No declaration was found in the file'),
            '158': self.env._('The form type mentioned in the file name does not match the form type present in the file'),
            '159': self.env._('Unable to assign an occupation number. Inconsistent data'),
            '160': self.env._('Incompatibility between postal code and municipality'),
            '161': self.env._('Cumulative deductions for non-admitted worker line'),
            '162': self.env._('Cumulative deductions for non-admitted occupation'),
            '163': self.env._('Form cannot be processed'),
            '164': self.env._('Late request from the authentic source'),
            '165': self.env._('Mixed declaration - employer category 021'),
            '166': self.env._('The ticket number mentioned is not known or is invalid'),
            '167': self.env._('A notification has already been recorded for the declaration with this ticket number'),
            '168': self.env._('Unauthorized access mode'),
            '169': self.env._('Severance or termination compensation present with other remuneration'),
            '170': self.env._("Incompatibility between the day's nature codes"),
            '171': self.env._('Isabel submission not signed or not compressed'),
            '172': self.env._('The number of declarations present in the file is larger than the number allowed for a file of this size'),
            '173': self.env._('Action authorized only for ONSS'),
            '174': self.env._('Action not authorized'),
            '175': self.env._('Inconsistent action codes'),
            '176': self.env._('Discrepancy with DmfA DB'),
            '177': self.env._('EmployerDeclarationPID - Discrepancy with DmfA DB'),
            '178': self.env._('DeclNaturalPersonPID - Discrepancy with DmfA DB'),
            '179': self.env._('NISS Unknown'),
            '180': self.env._('The modification or cancellation does not affect the last situation'),
            '181': self.env._('Modification or cancellation not authorized'),
            '182': self.env._('Not found in DmfA database'),
            '183': self.env._('A valid notification has already been recorded for this declaration'),
            '184': self.env._('The file size exceeds the imposed limit'),
            '185': self.env._('Average income too low'),
            '187': self.env._('Reservation not possible'),
            '188': self.env._('The form references more than one previously recorded form'),
            '189': self.env._('No sender number associated with the agent to which the employer is affiliated was found'),
            '190': self.env._('No sender number associated with this ONSS/PPL number was found'),
            '191': self.env._('The identification of the form referenced by this ticket number is not of the type expected'),
            '192': self.env._('Total number of days too high'),
            '193': self.env._('No output channel is associated with the agent to which the employer is affiliated'),
            '194': self.env._('No output channel is associated with the employer mentioned in the declaration'),
            '195': self.env._('The entity associated with the ONSS/PPL number mentioned is not a sender'),
            '196': self.env._('Incompatible with benefits'),
            '197': self.env._('A valid response has already been received or an impermissible response has been received for the form to which this document refers'),
            '198': self.env._('First engagement deduction code not present'),
            '201': self.env._('Maximum number of quarters exceeded'),
            '202': self.env._('Deduction code not applicable for the transitional measure'),
            '203': self.env._('Incompatible with the remuneration'),
            '204': self.env._('The qualification does not meet the criteria'),
            '205': self.env._('The file contains at least one data block that is not a form (Form block)'),
            '206': self.env._('Not intended for this worker'),
            '207': self.env._('Incompatible with the ONSS/PPL number and/or the NISS'),
            '208': self.env._("ONSS/PPL number - NISS - Period' combination not found in DIMONA"),
            '209': self.env._('NISS not included during the reference period'),
            '210': self.env._('Incompatibility with risk identification'),
            '211': self.env._('Incompatible with employer type'),
            '212': self.env._('Incompatible with worker status'),
            '213': self.env._('Invalid compensation code combination'),
            '214': self.env._('Incompatible with other quarters'),
            '215': self.env._('The FileReferenceNbr tag must be specified in the RFH2 and its value must be 13 characters long'),
            '216': self.env._('The WebChannel tag must be specified in the RFH2 and its value must be 0 or 1'),
            '217': self.env._('The DirectoryEnvironment tag must be specified in the RFH2 and its value must be 0, 1, or 3 (0, 1, or 3 if WebChannel = 0; 1 or 3 if WebChannel = 1)'),
            '218': self.env._('The UserId tag must be specified in the RFH2 and its value must have 6 numeric characters if WebChannel = 0 or 1 to 30 characters if WebChannel = 1'),
            '219': self.env._('The FormReferenceNbr tag must be specified in the RFH2 and its value must have 13 characters'),
            '220': self.env._('The ContentsStatus tag must be specified in the RFH2 and its value must be 0 or 3'),
            '221': self.env._('The SectorPointId tag must be specified in the RFH2'),
            '222': self.env._('The DataFormat tag must be specified in the RFH2 and its value must be 0 or 2'),
            '223': self.env._('The MessageCreationDate tag must be specified in the RFH2 and its value must be in the format YYYY-MM-DD'),
            '224': self.env._('The MessageCreationHour tag must be specified in the RFH2 and its value must be in the format format HH:mm:ss.SSS'),
            '225': self.env._('The ErrorId tag must be specified in the RFH2 and its value must be a maximum of 9 characters'),
            '226': self.env._('The Compressed tag must be specified in the RFH2 and its value must be 0 or 1'),
            '227': self.env._('The LengthNonCompressed tag must be specified in the RFH2 and its value must be numeric'),
            '228': self.env._('The LengthCompressed tag must be specified in the RFH2 and its value must be numeric'),
            '229': self.env._('Invalid compression algorithm'),
            '230': self.env._('Proxy not known for the employer'),
            '231': self.env._('Incompatibility with the sender'),
            '232': self.env._('No employer is associated with this natural person'),
            '233': self.env._('Incompatibility with the request'),
            '234': self.env._('Referenced form not found'),
            '235': self.env._('Not included in the directory'),
            '236': self.env._('The recipient of the form does not have an electronic channel'),
            '237': self.env._('Inconsistency between the form reference mentioned in the form and in its header'),
            '238': self.env._('Does not correspond to a form accepted by this sector'),
            '239': self.env._('Incompatibility with sectoral supplementary pension code'),
            '240': self.env._('We are not concerned by the request'),
            '241': self.env._('The referenced request or declaration has already been canceled'),
            '242': self.env._('End date of employment missing for at least one occupation'),
            '243': self.env._('Total number of days insufficient according to the work schedule within the occupation'),
            '244': self.env._('Incorrect occupancy fraction'),
            '245': self.env._('To be checked'),
            '246': self.env._('The message contains more than one form'),
            '247': self.env._('The completed occupancy is not found'),
            '248': self.env._('The routing recipient is not known'),
            '249': self.env._('The channel is different from the one listed in the access directory'),
            '250': self.env._('Incomplete declaration: too few workers declared'),
            '251': self.env._('Already responded to by a declaration made on your own initiative'),
            '252': self.env._('NISS number changed'),
            '253': self.env._('The data used to route the message is missing or invalid'),
            '254': self.env._('The expected sequence number was not entered or is invalid'),
            '255': self.env._('The submitted form is not valid according to the data model'),
            '256': self.env._('The expected ticket number was not specified'),
            '257': self.env._('A file or message with an S environment was deposited in a directory other than INTEST-S or in a queue not reserved for testing'),
            '258': self.env._('Incompatibility between the value of the Identification tag and the value of the Environment tag provided in the RFH2 of a message'),
            '259': self.env._('Compensation to be declared in the quarter in which the base salary was declared'),
            '260': self.env._('Number of hours too high'),
            '261': self.env._('The quarterly reference salary does not meet the conditions.'),
            '262': self.env._('More workers declared in DmfA than in DIMONA'),
            '263': self.env._('Fewer workers declared in DmfA than in DIMONA'),
            '264': self.env._('Date not possible'),
            '265': self.env._('Unauthorized employment contract type'),
            '267': self.env._('The publication format was not specified or is incorrect'),
            '268': self.env._('Incompatibility with the personnel file'),
            '269': self.env._('Incompatibility with Dimona'),
            '270': self.env._('Submission deadline not met'),
            '271': self.env._('Maximum period exceeded'),
            '272': self.env._('Already processed or declared'),
            '273': self.env._('Contribution required according to current conditions'),
            '274': self.env._('Invalid attribute'),
            '275': self.env._('The number of authorized forms has been exceeded'),
            '276': self.env._('Incompatibility with the ONEM file'),
            '277': self.env._('Application canceled by the social security transfer point'),
            '278': self.env._("Employment start date prior to the employer's registration date"),
            '280': self.env._('Invalid ZIP file'),
            '281': self.env._('Incorrect ZIP file (contains no file or more than one file)'),
            '282': self.env._('Too many mailbox tags present in the file'),
            '283': self.env._('Presence of a record that does not match the fileType mentioned in the Mailbox element'),
            '284': self.env._('Absence of declaration or inconsistency with the record attribute'),
            '285': self.env._('The serviceName attribute of the Mailbox tag is not present'),
            '286': self.env._('The serviceName attribute of the Mailbox tag is unknown'),
            '287': self.env._('The fileType attribute of the Mailbox tag is not present'),
            '288': self.env._('The value of the fileType attribute is not compatible with the serviceName'),
            '289': self.env._('The Records attribute of the Mailbox tag is not present'),
            '290': self.env._('The value of the Records attribute of the Mailbox tag is non-numeric'),
            '291': self.env._('The environment attribute of the Mailbox tag is not present'),
            '292': self.env._('The value of the environment attribute of the Mailbox tag is not consistent with the environment stipulated in the file name'),
            '293': self.env._('The value of The sectorDestination attribute of the Mailbox tag does not exist for the specified serviceName'),
            '294': self.env._('The CBSS/Reference tag is not present in the MessageContext tag'),
            '295': self.env._('The CBSS/TreatmentTime tag is not present in the MessageContext tag'),
            '296': self.env._("The CBSS/TreatmentTime tag does not match the expected format (yyyy-MMdd'T'HH:mm:ss.SSS)"),
            '297': self.env._('The id attribute of the Service tag is not present'),
            '298': self.env._('The id attribute of the Service tag does not match the serviceName attribute of the Mailbox tag'),
            '299': self.env._('No Data tag in the record'),
            '300': self.env._('The version attribute of the Service tag is not present'),
            '301': self.env._('The version attribute of the Service tag contains an unknown version ID'),
            '302': self.env._('Multiple different versions are referenced in different records in the file'),
            '303': self.env._("The destination 'sector-institution' of the MessageContext tag does not match the destination 'sector-institution' of the Mailbox tag"),
            '304': self.env._("No Destination institution attributes in the 'Mailbox' tag"),
            '305': self.env._("The destination 'sector-institution' of the Mailbox tag is unknown"),
            '306': self.env._("The destination 'sector-institution' of the Mailbox tag is invalid (non-numeric)."),
            '307': self.env._('The Destination tag is not present in the record'),
            '308': self.env._('More than one Destination tag present in the record'),
            '309': self.env._('No institution attribute present in the tag Destination'),
            '310': self.env._('No sector attribute present in the Destination tag'),
            '311': self.env._('The values of the institution and sector attributes in the Destination tag are incorrect'),
            '312': self.env._('The file is not valid based on the associated data models (XML schema)'),
            '313': self.env._('Warning! Quarter in danger of being time-barred or time-barred.'),
            '314': self.env._('Joint Committee 999 not allowed'),
            '316': self.env._('Contribution type - combination not allowed'),
            '317': self.env._('The total number of records specified in a Mailbox A1 header is not numeric'),
            '318': self.env._('The total number of bytes specified in a Mailbox A1 header is not numeric'),
            '319': self.env._('The total number of bytes specified in a Mailbox A1 header is incorrect'),
            '320': self.env._('Incorrect prefix type for an ACR'),
            '321': self.env._('Incorrect processing type for an ACR'),
            '322': self.env._('Unknown flow success code for an ACR'),
            '323': self.env._('Required declaration: Mixture of credits and debits not allowed'),
            '324': self.env._('Required declaration: Too many items'),
            '325': self.env._('Required declaration'),
            '326': self.env._('Info: Calculated balance'),
            '330': self.env._('Start and/or end date of the occupation line outside the validity period'),
            '333': self.env._('Duplicate Dimona period'),
            '334': self.env._('Overlapping'),
            '336': self.env._('Prohibited from making Dimona-Full and Dimona-Light declarations for the same day'),
            '337': self.env._('Prohibited from having multiple Dimona-light periods for the same day'),
            '338': self.env._("Incompatibility with the employer's daily reporting type (full/light)"),
            '339': self.env._('Missing service type or end date and time'),
            '340': self.env._('Prohibited from stating both the service type and the end date and time'),
            '341': self.env._('Period too long (>24h)'),
            '342': self.env._('Reporting only via a secure channel for this employer'),
            '343': self.env._('Employer not or no longer active in the employer directory'),
            '344': self.env._('Prohibited from postponing'),
            '345': self.env._('End time earlier than start time'),
            '346': self.env._('Employer has not yet opted for Dimona New'),
            '347': self.env._('Incompatible with the Dimona period identification number'),
            '348': self.env._('Incompatible with the NISS'),
            '349': self.env._('Incompatibility between joint committee and type of worker'),
            '350': self.env._('Type of worker prohibited for this employer'),
            '351': self.env._('Missing company number or name'),
            '352': self.env._('Prohibited from mentioning both company number and name'),
            '353': self.env._('Same C3.2A card number as the previous month'),
            '354': self.env._('Unknown Dimona period identification number'),
            '355': self.env._('Dimona period or daily record already canceled'),
            '356': self.env._('Dimona period already closed'),
            '357': self.env._('Dimona period with blocking anomaly'),
            '359': self.env._('Prohibited from submitting a change declaration to close a Dimona period'),
            '360': self.env._('Start and/or end date required'),
            '361': self.env._('Start date/time and/or end date/time required'),
            '362': self.env._('Prohibited from submitting Dimona declarations for a locked period'),
            '363': self.env._('NISS or identification data required'),
            '364': self.env._('ONSS number or company number required'),
            '366': self.env._('Non-existent participant on the declaration'),
            '367': self.env._('The submission number specified in the file name or RFH2 contains a character other than 0 to 9 and A to Z'),
            '368': self.env._('Prohibited from deleting the end date for this period'),
            '369': self.env._('Exceeding the quota'),
            '370': self.env._('Start or end date after 12/31/2011 not permitted for a student'),
            '371': self.env._('Incompatible with the Collective Social Service'),
            '372': self.env._('Incompatible with the date of first granting of the allowance'),
            '373': self.env._('Incompatible with the concept of part-time'),
            '374': self.env._('Incompatible with the concept of a company in difficulty or undergoing restructuring'),
            '375': self.env._('Incompatible with the date of notification of the notice'),
            '376': self.env._('Incompatible with the concept of a compliant replacement'),
            '377': self.env._('Number of months too high'),
            '378': self.env._("Incorrect number of months for the employer's share"),
            '379': self.env._('Value not permitted for this employer'),
            '380': self.env._('Value not authorized for this period'),
            '381': self.env._('Incompatible with the staff category'),
            '382': self.env._('The amount does not correspond to the prorated minimum'),
            '383': self.env._('The employer entered must be different from the reporting employer'),
            '384': self.env._('Incompatibility between employer and 2nd pension pillar'),
            '388': self.env._('Start date later than the start date of the parent block'),
            '389': self.env._('Hap between two occupations (or career elements) with reason for termination of the statutory relationship'),
            '390': self.env._('Hap between occupations (or career elements)'),
            '391': self.env._('Hap between salaries'),
            '392': self.env._('Incompatible with the end date of the parent block'),
            '393': self.env._('Lines of Public sector occupation data not strictly successive'),
            '394': self.env._('Most recent certificate already received for this worker and this reporting employer'),
            '395': self.env._('Incompatibility between the worker and the reporting employer'),
            '396': self.env._('Mandatory employer identifier'),
            '397': self.env._('No career element declared for 31/12/2010'),
            '398': self.env._('Reason for termination of statutory relationship or career element with the reporting employer missing'),
            '399': self.env._('Start date earlier than the start date of the parent block'),
            '400': self.env._('End date later than the end date of the parent block'),
            '401': self.env._('Incompatible with the declared career elements'),
            '402': self.env._('Incompatible with the nature of the employment relationship'),
            '403': self.env._('Incompatible with the type of contract'),
            '404': self.env._('Incompatible with the work reorganization measure'),
            '405': self.env._('Incorrect number of months for the personal portion'),
            '406': self.env._('Absence of Capelo block in the DmfA(PPL) for this worker and this reporting employer'),
            '407': self.env._('Declaration for another employer employing the worker on 12/31/2010 prohibited'),
            '408': self.env._('Gap between the last career element and the occupation declared in the DmfA(PPL)'),
            '409': self.env._('Incompatibility between the DmfA(PPL) worker code and the nature of the employment relationship'),
            '410': self.env._('Difference with the data declared in DmfA(PPL)'),
            '411': self.env._('Impossibility of having two main or secondary careers with the same employer'),
            '412': self.env._('Salary scale block not present for the reporting employer'),
            '413': self.env._('Incompatible with the absence code'),
            '414': self.env._('Incompatible with the start date of the parent block'),
            '415': self.env._('Incompatible with the amount of the previous salary scale'),
            '416': self.env._('End date of the career element is later than 12/31/2010'),
            '418': self.env._('Incompatible with the occupation data relating to the public sector'),
            '419': self.env._('More contributions due'),
            '420': self.env._('The number of days declared exceeds the number of days in the period'),
            '421': self.env._('The period start and end dates must fall within the same quarter'),
            '422': self.env._("Inconsistency between the number of hours per week and the worker's average number of hours per week"),
            '423': self.env._('Previous certificate already modified via the web application'),
            '424': self.env._('Career Element block not present for this employer'),
            '425': self.env._('Date of taking up a new position after the end date of the salary scale'),
            '426': self.env._('Extra-statutory pension contribution (sectoral or company pension plan) not present'),
            '427': self.env._('No authorization'),
            '428': self.env._('The employer remains silent'),
            '429': self.env._('Number of days declared in DMFA different from the number of days declared in DIMONA'),
            '430': self.env._('The file(s) causing problems during the initial submission have been deleted.'),
            '433': self.env._('Salary scale block only expected for the reporting employer'),
            '434': self.env._('Difference in employment contract type compared to the previous career element'),
            '435': self.env._('Continuing career with the same employer'),
            '436': self.env._('Batch submission not authorized for this type of historical certificate'),
            '437': self.env._('Start date prior to the certificate eligibility date'),
            '438': self.env._('Another employer has submitted at least one DmfA(PPL) after 01/01/2011'),
            '439': self.env._('Statutory employment relationship not authorized for 01/01/2011'),
            '440': self.env._('Total percentage incorrect'),
            '441': self.env._('Number of hours/week greater than the number of hours/week - full salary scale'),
            '442': self.env._('Number of hours/week - salary scale greater than the number of hours/week of the person. of reference'),
            '443': self.env._('Number of hours/week - salary scale lower than the number of hours/week of the reference person'),
            '444': self.env._('No change detected'),
            '445': self.env._('No career element with the reporting employer'),
            '448': self.env._('Incompatible with the job number'),
            '449': self.env._('Salary too high'),
            '450': self.env._('Declaration type temporarily prohibited for the selected period'),
            '451': self.env._('Employer incompatibility'),
            '452': self.env._('Unable to determine a time indication for social risk'),
            '453': self.env._('Does not correspond to a form rejected by this sector'),
            '455': self.env._('Unable to identify the recipient'),
            '456': self.env._('No Dimona as a casual worker for this occupation'),
            '459': self.env._('Prohibited from having casual periods lasting more than two consecutive days'),
            '460': self.env._('Late declaration'),
            '461': self.env._('The employer has not opted for the Dimona system for their daily records'),
            '462': self.env._('Incompatibility between daily records and the Dimona period'),
            '468': self.env._('ECB data to be verified'),
            '469': self.env._('Incompatible with the annual reference salary'),
            '471': self.env._('Deduction code not present or incompatible'),
            '472': self.env._('Does not meet the fund conditions'),
            '473': self.env._('Incompatible with the concept of exemption from supplementary pension scheme'),
            '474': self.env._('Reduction not applicable based on the number Local unit identification number'),
            '475': self.env._('Reduction not applicable for the region'),
            '476': self.env._('Special contribution on severance pay not present'),
            '477': self.env._('The geolocation of the address provided in the declaration is inaccurate'),
            '478': self.env._('The severance pay begins before the end of paid employment'),
            '480': self.env._('Public sector pension contribution not present'),
            '481': self.env._('Incompatible with the public sector pension code'),
            '482': self.env._('Incompatible with the original declaration or the latest status of this declaration'),
            '483': self.env._('Applicable if the conditions are met'),
            '484': self.env._('Flexijob employment covered fully or partially by a severance payment'),
            '485': self.env._('Flexijob employment not covered or not fully covered by Dimona'),
            '486': self.env._('Flexijob cannot be combined with a contract of 80% or more'),
            '487': self.env._('Incompatible with the FPS Employment data'),
            '488': self.env._('Incompatible with the recognition period'),
            '489': self.env._('Incompatible with the ministerial decision date'),
            '490': self.env._("Incompatible with the date of the dismissal announcement collective"),
            '491': self.env._('Incompatible with the interruption of employment code'),
            '492': self.env._('Incompatible with the validity period of the collective agreement'),
            '493': self.env._('The requested period is too short'),
            '494': self.env._('The requested period is too long'),
            '495': self.env._('Incompatible with the sector'),
            '496': self.env._('Incompatible with the type of interruption'),
            '497': self.env._("Incompatible with the worker's working hours"),
            '498': self.env._('Incomplete questionnaire'),
            '499': self.env._('The worker does not meet the conditions for access to this type of interruption'),
            '500': self.env._('Incompatible with the number of workers'),
            '501': self.env._('Incompatible with the type of day code'),
            '502': self.env._("Difference in hours in DmfA - scheduled hours in Dimona with reduced contributions"),
            '503': self.env._('More than 6 consecutive days of temporary unemployment'),
            '504': self.env._('No scheduled hours in Dimona eligible for reduced social security contributions'),
            '505': self.env._('Form cannot be processed in sequence'),
            '506': self.env._('Specific request - Please submit a paper form'),
            '507': self.env._('Obsolete request'),
            '508': self.env._('More than one enhanced form sent for the original form'),
            '509': self.env._('Total size of FI and FS files exceeds the imposed limit after compression'),
            '510': self.env._('Flexi-Jobs access conditions not met'),
            '511': self.env._('Incompatible with the training situation'),
            '512': self.env._("Incompatible with the ship's identification number"),
            '513': self.env._('Unknown to the authentic source'),
            '514': self.env._('Young worker without experience'),
            '515': self.env._('Technical problem: Unable to check the "Young worker without experience" status'),
            '516': self.env._('Starter-Jobs access conditions not met'),
            '517': self.env._('Incompatible with the type of public sector institution'),
            '518': self.env._('Second pillar pension data missing'),
            '519': self.env._('Retired before 01/01/2016'),
            '520': self.env._('Retired after 31/12/2015'),
            '521': self.env._('Incompatible with the nature of the employment'),
            '522': self.env._('Not within the scope of application - AMI Indemnités Scheme'),
            '523': self.env._('NISS not processed by this recipient'),
            '524': self.env._('Signature not possible'),
            '525': self.env._('Conversion to PDF not possible'),
            '526': self.env._('Risk paid by the employer'),
            '527': self.env._('Incompatible with the employment promotion measure'),
            '528': self.env._('Calculation basis for the special contribution for the Corona bonus or purchasing power bonus too high'),
            '529': self.env._('Total inconsistency of the contribution calculation bases - total compensation.'),
            '532': self.env._('Incompatibility with the concept of pensioner'),
            '533': self.env._('Incompatibility with the country code'),
            '534': self.env._('No entitlement based on the data from the authentic source'),
            '535': self.env._('Flexijob cannot be combined with another employment relationship'),
            '536': self.env._('Not within the scope of Flexijob'),
        }
        return error_messages.get(code, self.env._('Unknown Error Label'))

    def _get_diagnosis_label(self, code):
        error_messages = {
            '0': self.env._("Incomplete declaration"),
            '1': self.env._("Too many missing Dimona entries"),
            '2': self.env._("Too many missing NISS numbers"),
            '3': self.env._("Declaration rejected - blocking anomalies"),
            '4': self.env._("Declaration rejected - too many anomalies"),
            '5': self.env._("Employer not authorized for auto-validation"),
            '6': self.env._("Inactive certificate"),
            '7': self.env._("Presence of anomaly/anomalies"),
            '8': self.env._("Presence of a web certificate"),
            '9': self.env._("Auto-validation not requested"),
        }
        return error_messages.get(code, self.env._('Unknown Diagnosis Label'))

    def _get_anomaly_class_label(self, code):
        error_messages = {
            "B": self.env._("Blocking anomaly"),
            "P": self.env._("Percentage-based anomaly"),
            "NP": self.env._("Non-percentage-based anomaly"),
            "D": self.env._("Anomaly related to deduction rights verification"),
            "W": self.env._("Warning"),
            "I": self.env._("Investigation"),
        }
        return error_messages.get(code, self.env._('Unknown Anomaly Class Label'))
