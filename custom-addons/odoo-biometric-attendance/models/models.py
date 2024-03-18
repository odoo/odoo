# -*- coding: utf-8 -*-

import requests
from odoo import models, fields, api, exceptions, _
from odoo.exceptions import Warning

DEVICE_API_BASE_URL = 'http://robot.camsunit.com/external/1.0/user'

class Attendance(models.Model):
    
    _inherit = 'hr.attendance'

    machine_id = fields.Char(string="Biometric Device ID")
    check_in = fields.Datetime(string="Check In", default=False, required=False)


    @api.constrains('check_in', 'check_out', 'employee_id')
    def _check_validity(self):
        """Override the validations to receive any kind of data
        """
        pass

    @api.constrains('check_in', 'check_out')
    def _check_validity_check_in_check_out(self):
        """Override the validations to receive any kind of data
        """
        pass
    
    # @api.depends('check_in', 'check_out')
    # def _compute_worked_hours(self):
    #     """Override the validations to receive any kind of data
    #     """
    #     pass

    @api.depends('check_in', 'check_out')
    def _compute_worked_hours(self):
        for attendance in self:
            if attendance.check_in and attendance.check_out:
                delta = attendance.check_out - attendance.check_in
                attendance.worked_hours = delta.total_seconds() / 3600.0
            else:
                attendance.worked_hours = False

    worked_hours = fields.Float(string='Worked Hours', compute='_compute_worked_hours', store=True, readonly=True)

    def name_get(self):
        result = []
        for attendance in self:
            if not attendance.check_out:
                result.append((attendance.id, _("Attendance for %(empl_name)s") % {
                    'empl_name': attendance.employee_id.name,
                }))
            else:
                result.append((attendance.id, _("Attendance for %(empl_name)s ") % {
                    'empl_name': attendance.employee_id.name,                   
                }))
        return result




class DeviceServiceTag(models.Model):

    _name = 'device.service.tag'

    _rec_name = 'service_tag_id' 

    service_tag_id = fields.Char('Service Tag ID', required=True)
    auth_token = fields.Char('Authentication Token', required=True)
    #last_connection = fields.Datetime('Last Connection')


class HrEmployee(models.Model):
    
    _inherit = 'hr.employee'

    service_tag_ids = fields.Many2many('device.service.tag')    
    employee_ref = fields.Char('Biometric User ID', required=True)


    def check_device_config(self):
        config = self.env['res.config.settings'].search([])
        try:
            update_device = config[-1].update_device
            if update_device:
                return True
            return False
        except:
            return False
        
    @api.model
    def create(self, vals):
        update_device = self.check_device_config()
        res = super(HrEmployee, self).create(vals)
        if update_device:
            for stgid in res.service_tag_ids:
                data={'stgid':stgid.service_tag_id, 'uid':res.employee_ref, 'uname':res.name}
                try:
                    device_user = requests.post(DEVICE_API_BASE_URL+'/add', data)
                    print(device_user.text)

                except:
                    raise Warning('Error Creating User to - %s ') % (stgid.service_tag_id)
        return res

    def unlink(self):
        update_device = self.check_device_config()
        if update_device:
            for stgid in self.service_tag_ids:
                data={'stgid':stgid.service_tag_id, 'uid':self.employee_ref}
                try:
                    device_user = requests.post(DEVICE_API_BASE_URL+'/delete', data)
                    print(device_user.text)
                except:
                    raise Warning('Error Removing User to - %s ') % (stgid.service_tag_id)
        res = super(HrEmployee, self).unlink()
        return res


    def write(self, vals):
        update_device = self.check_device_config()
        
        # TODO : CHECK IF THIS DOUBLE CHECK IS 
        # NEEDED OR BYPASS IF COMING FROM DEVICE

        if vals.get('service_tag_ids') and update_device:
            new_stg_ids = vals.get('service_tag_ids')[0][2]
            existing_stg_ids = [x.id for x in self.service_tag_ids]
            add_diff = [item for item in new_stg_ids if item not in existing_stg_ids]
            removal_diff = [item for item in existing_stg_ids if item not in new_stg_ids ]
            
            if len(removal_diff) > 0:
                for stgid in removal_diff:
                    service_tag = self.env['device.service.tag'].browse(stgid)
                    data={'stgid': service_tag.service_tag_id, 'uid': self.employee_ref}
                    try:
                        device_user = requests.post(DEVICE_API_BASE_URL+'/delete', data)
                        print(device_user.text)

                    except:
                        raise Warning('Error Removing User to - {}'.format(service_tag.service_tag_id))

            if len(add_diff) > 0:
                for stgid in add_diff:
                    service_tag = self.env['device.service.tag'].browse(stgid)
                    data={'stgid':service_tag.service_tag_id, 'uid':self.employee_ref, 'uname':self.name}
                    
                    try:
                        device_user = requests.post(DEVICE_API_BASE_URL+'/add', data)
                        print(device_user.text)
                    except:
                        raise Warning('Error Creating User to - {}'.format(service_tag.service_tag_id))
                        
        res = super(HrEmployee, self).write(vals)
        return res
