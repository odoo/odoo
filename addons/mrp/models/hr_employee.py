from odoo import models
from odoo.http import request
from datetime import datetime

EMPLOYEES_CONNECTED = "employees_connected"
SESSION_OWNER = "session_owner"


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    """ Use the session to remember the current employee between views.
        The main purpose is to avoid a hash implementation on client side.

        The sessions have two main attributes :
            - employees_connected : the list of connected employees in the session
            - session_owner : the main employee of the session. Only the session_owner can start/stop a running workorder.
    """

    def pin_validation(self, pin=False):
        if not pin:
            pin = False
        return self.sudo().pin == pin

    def login(self, pin=False):
        if self.pin_validation(pin):
            self._connect_employee()
            request.session[SESSION_OWNER] = self.id
            return True
        return False

    def logout(self, pin=False):
        # For some reason, if the session owner does not get changed during a run of this logout function, the writes
        # to the connected employees are not persisted in the session. To hack around this we always set the owner
        # to the user that is logging out, and we change it back after (or to False if the admin logs out).
        employees = request.session.get(EMPLOYEES_CONNECTED, [])
        owner = request.session.get(SESSION_OWNER, False)
        if self.id in employees:
            request.session[SESSION_OWNER] = self.id
            employees.remove(self.id)
            request.session[EMPLOYEES_CONNECTED] = employees
            if owner == self.id:
                owner = False
            request.session[SESSION_OWNER] = owner
            return True
        return False

    def remove_session_owner(self):
        self.ensure_one()
        if self.id == request.session.get(SESSION_OWNER):
            request.session[SESSION_OWNER] = False

    def _connect_employee(self):
        """
            This function sets the employee that is connecting (or that is already connected)
            as the first element of the array
        """
        employees = request.session.get(EMPLOYEES_CONNECTED, [])
        if len(employees) == 0:
            request.session[EMPLOYEES_CONNECTED] = [self.id]
            return
        if self.id not in employees:
            request.session[EMPLOYEES_CONNECTED] = [self.id] + employees

    def get_employees_wo_by_employees(self, employees_ids):
        """
            returns the workorders "in progress" associated to the employees passed in params (where they have already timesheeted)
        """
        employees = [{'id': employee_id} for employee_id in employees_ids]
        workorders = self.env['mrp.workorder'].search([('state', '=', 'progress')])
        time_ids = self.env['mrp.workcenter.productivity']._read_group(
            ['&', ('employee_id', 'in', employees_ids), ('workorder_id', 'in', workorders.ids)],
            ['employee_id', 'workorder_id'],
            ['duration:sum', 'date_end:array_agg', 'date_start:array_agg'],
        )

        for emp in employees:
            emp["workorder"] = []
        for employee, workorder, duration, end_dates, start_dates in time_ids:
            if any(not date for date in end_dates):
                duration = int((datetime.now() - (max(start_dates))).total_seconds()) / 60

                employee = next(emp for emp in employees if emp['id'] == employee.id)
                employee["workorder"].append(
                    {
                        'id': workorder.id,
                        'work_order_name': workorder.production_id.name,
                        'duration': duration,
                        'operation_name': workorder.operation_id.name,
                        'ongoing': True
                    })
        return employees

    def stop_all_workorder_from_employee(self):
        """
            This stops all the workorders that the employee is currently working on
            We could use the stop_employee from mrp_workorder but it implies that me make several calls to the backend:
            1) get all the WO
            2) stop the employee on these WO
        """
        work_orders = self.env['mrp.workorder'].search(['&', ('state', '=', 'progress'), ('employee_ids.id', 'in', self.ids)])
        work_orders.stop_employee(self.ids)

    def get_employees_connected(self):
        if request:
            return request.session.get(EMPLOYEES_CONNECTED, [])
        # Test cases
        return [self.env.user.employee_id.id]

    def get_session_owner(self):
        if request:
            return request.session.get(SESSION_OWNER, [])
        # Test cases
        return [self.env.user.employee_id.id]

    def login_user_employee(self):
        if self.get_session_owner():
            return
        # If no admin is set, try to set the users employee as admin.
        user_employee = self.env.user.employee_id
        if user_employee and user_employee.login():
            return
        # If the user does not have an employee set, try the other logged in employees.
        for employee in self.get_employees_connected():
            if self.browse(employee).login():
                return
        # Just show the user's employee in the list.
        if user_employee:
            user_employee._connect_employee()

    def get_all_employees(self, login=False):
        if login:
            self.login_user_employee()

        companies_ids = self.env.companies.ids
        all_employees = self.search_read(['|', ('company_id', '=', False), ('company_id', 'in', companies_ids)], fields=['id', 'name'])

        all_employees_ids = {employee['id'] for employee in all_employees}
        employees_connected = list(filter(
            lambda employee_id: employee_id in all_employees_ids, self.get_employees_connected()))
        out = {
            'admin': self.get_session_owner(),
            'connected': self.get_employees_wo_by_employees(employees_connected)
        }
        if login:
            out['all'] = all_employees
        return out
