# En mi_website_ext/models/res_users.py
from odoo import models, fields, api
from datetime import date 
from dateutil.relativedelta import relativedelta # Para cálculos de mes
from odoo.tools.misc import format_date # Para formateo de fecha localizado
import logging
_logger = logging.getLogger(__name__)

class Users(models.Model):
    _inherit = 'res.users'
    
    x_terms_accepted = fields.Boolean(string="Accepted Terms and Conditions", default=False)

    x_has_accepted_policies = fields.Boolean(
        string="Ha aceptado políticas obligatorias", 
        default=False
    )

    x_has_updated_profile = fields.Boolean(string="Ha actualizado su perfil inicial", default=False)

    x_days_until_vacation_display = fields.Char(
        string="Días Para Próximas Vacaciones",
        compute='_compute_days_until_next_vacation',
        store=False 
    )

    x_available_remunerated_permission_hours = fields.Char(
        string="Horas de Permiso Remunerado Disponibles", 
        compute='_compute_remunerated_permission_hours',
        store=False
    )

    x_employee_first_contract_date = fields.Date(
        string="Fecha Primer Contrato (para Aniversario)",
        compute='_compute_anniversary_details',
        store=False # Se calcula al vuelo
    )
    
    # Guardamos los años cumplidos para usar en QWeb
    x_employee_years_in_company = fields.Integer(
        string="Años en Compañía (Aniversario)",
        compute='_compute_anniversary_details',
        store=False
    )

    x_days_in_company = fields.Integer(
        string="Días en la Compañía",
        compute='_compute_days_in_company'
    )

    @api.depends_context('uid')
    def _compute_days_until_next_vacation(self):
        today = fields.Date.context_today(self)
        HrLeave = self.env['hr.leave']
        HrEmployee = self.env['hr.employee']


        for user in self:
            vacation_leave_type = self.env['hr.leave.type'].sudo().search([('name', '=', 'Vacaciones'), ('company_id', 'in', [user.company_id.id, False])], limit=1) # Asume que el nombre es exactamente "Vacaciones"
            vacation_leave_type_id = vacation_leave_type.id if vacation_leave_type else None

            if not vacation_leave_type:
                user.x_days_until_vacation_display = "--"
                continue 
            
            employee = HrEmployee.sudo().search([('user_id', '=', user.id), ('company_id', 'in', [user.company_id.id, False])], limit=1)
            if not employee:
                user.x_days_until_vacation_display = "--"
                continue

            domain = [
                ('employee_id', '=', employee.id),
                ('state', '=', 'validate'),  # Solo ausencias aprobadas
                ('request_date_to', '>', today), # Que empiecen después de hoy
                ('holiday_status_id', '=', vacation_leave_type_id), # Solo tipo "Vacaciones"
            ]

            next_vacation = HrLeave.sudo().search(domain, order='request_date_from asc', limit=1)

            if next_vacation and next_vacation.request_date_from:
                vacation_start_date = next_vacation.request_date_from
                vacation_end = next_vacation.request_date_to or vacation_start_date
                if vacation_start_date <= today <= vacation_end:
                    user.x_days_until_vacation_display = "VA"
                else: 
                    delta = vacation_start_date - today
                    days_remaining = delta.days
                    
                    if days_remaining == 0:
                        user.x_days_until_vacation_display = "Hoy"
                    elif days_remaining == 1:
                        user.x_days_until_vacation_display = "1"
                    else:
                        user.x_days_until_vacation_display = str(days_remaining)
            else:
                    user.x_days_until_vacation_display = "N/A"

    @api.depends_context('uid')
    def _compute_remunerated_permission_hours(self):
        monthly_allowance_hours = 8.0 
        today = fields.Date.context_today(self)
        first_day_current_month = today.replace(day=1)
        last_day_current_month = (today.replace(day=1) + relativedelta(months=1) - relativedelta(days=1))

        HrEmployee = self.env['hr.employee']
        HrLeave = self.env['hr.leave']

        for user in self:
            permission_leave_type = self.env['hr.leave.type'].sudo().search([
                ('name', '=', 'Solicitud de permiso'),
                ('company_id', 'in', [user.company_id.id, False])
            ], limit=1)

            if not permission_leave_type:
                _logger.error("Tipo de ausencia 'Solicitud de permiso' no encontrado para la compañía del usuario %s (ID %s).", user.name, user.company_id.id)
                user.x_available_remunerated_permission_hours = "Error Conf."
                continue

            permission_leave_type_id = permission_leave_type.id

            employee = HrEmployee.sudo().search([('user_id', '=', user.id)], limit=1)
            if not employee:
                user.x_available_remunerated_permission_hours = "--"
                continue

            domain = [
                ('employee_id', '=', employee.id),
                ('holiday_status_id', '=', permission_leave_type_id),
                ('state', 'in', ['confirm', 'validate']),
                ('request_date_from', '<=', last_day_current_month),
                ('request_date_to', '>=', first_day_current_month),
            ]

            approved_permissions = HrLeave.search(domain)
            hours_taken_this_month = 0.0

            for leave in approved_permissions:
                if hasattr(leave, 'number_of_hours_display') and leave.request_unit_hours:
                    hours_taken_this_month += leave.number_of_hours_display
                elif hasattr(leave, 'number_of_days'):
                    hours_per_day = employee.resource_calendar_id.hours_per_day or 8.0
                    hours_taken_this_month += leave.number_of_days * hours_per_day
                else:
                    duration_str = leave.duration_display
                    try:
                        if 'hour' in duration_str.lower():
                            parts = duration_str.split(' ')[0].split(':')
                            if len(parts) == 2:
                                hours = float(parts[0])
                                minutes = float(parts[1])
                                hours_taken_this_month += hours + (minutes / 60.0)
                            elif len(parts) == 1 and duration_str.split(' ')[0].replace('.', '', 1).isdigit():
                                hours_taken_this_month += float(parts[0])
                        elif 'day' in duration_str.lower():
                            days = float(duration_str.split(' ')[0])
                            hours_per_day_calendar = employee.resource_calendar_id.hours_per_day or 8.0
                            hours_taken_this_month += days * hours_per_day_calendar
                    except ValueError:
                        _logger.warning(f"No se pudo parsear duration_display: '{duration_str}' para la ausencia ID {leave.id}")

            remaining_hours = monthly_allowance_hours - hours_taken_this_month
            user.x_available_remunerated_permission_hours = f"{max(0, remaining_hours):.0f}H"


    def get_available_permission_hours(self, employee, date_from, date_to):
        """
        Devuelve cuántas horas disponibles tiene el empleado en el mes del permiso solicitado.
        Se usa para validación al momento de crear permisos.
        """
        monthly_allowance_hours = 8.0
        start_of_month = date_from.replace(day=1)
        end_of_month = (start_of_month + relativedelta(months=1)) - relativedelta(days=1)

        permission_leave_type = self.env['hr.leave.type'].sudo().search([
            ('name', '=', 'Solicitud de permiso'),
            ('company_id', 'in', [employee.company_id.id, False])
        ], limit=1)

        if not permission_leave_type:
            return 0.0

        domain = [
            ('employee_id', '=', employee.id),
            ('holiday_status_id', '=', permission_leave_type.id),
            ('state', 'in', ['confirm', 'validate']),
            ('request_date_from', '<=', end_of_month),
            ('request_date_to', '>=', start_of_month),
        ]

        HrLeave = self.env['hr.leave']
        leaves = HrLeave.sudo().search(domain)

        hours_taken = 0.0
        for leave in leaves:
            if hasattr(leave, 'number_of_hours_display') and leave.request_unit_hours:
                hours_taken += leave.number_of_hours_display
            elif hasattr(leave, 'number_of_days'):
                hours_per_day = employee.resource_calendar_id.hours_per_day or 8.0
                hours_taken += leave.number_of_days * hours_per_day
            else:
                try:
                    duration_str = leave.duration_display
                    if 'hour' in duration_str.lower():
                        parts = duration_str.split(' ')[0].split(':')
                        if len(parts) == 2:
                            hours = float(parts[0])
                            minutes = float(parts[1])
                            hours_taken += hours + (minutes / 60.0)
                        elif len(parts) == 1 and duration_str.split(' ')[0].replace('.', '', 1).isdigit():
                            hours_taken += float(parts[0])
                    elif 'day' in duration_str.lower():
                        days = float(duration_str.split(' ')[0])
                        hours_per_day = employee.resource_calendar_id.hours_per_day or 8.0
                        hours_taken += days * hours_per_day
                except Exception as e:
                    _logger.warning(f"Error al parsear duration_display: {e}")

        return max(0, monthly_allowance_hours - hours_taken)

     # Método de cómputo para los detalles del aniversario
    
    @api.depends_context('uid') 
    def _compute_anniversary_details(self):
        today = fields.Date.context_today(self) 
        current_month = today.month
        current_year = today.year
        
        HrEmployee = self.env['hr.employee']
        HrContract = self.env['hr.contract']

        for user in self: # 'user' aquí es un registro de res.users
            user.x_employee_first_contract_date = False
            user.x_employee_years_in_company = 0 # Valor por defecto importante

            employee = HrEmployee.search([('user_id', '=', user.id)], limit=1)
            if not employee:
                _logger.debug(f"Aniversario: No se encontró empleado para usuario {user.name} (ID: {user.id})")
                continue

            first_contract = HrContract.search([
                ('employee_id', '=', employee.id),
                ('date_start', '!=', False),
                ('date_start', '<=', today) # El contrato debe haber iniciado
            ], order='date_start asc', limit=1)

            _logger.debug(f"Aniversario - Usuario: {user.name}, Empleado: {employee.name}, Contrato ID: {first_contract.id if first_contract else 'N/A'}, Fecha Contrato: {first_contract.date_start if first_contract else 'N/A'}")

            if first_contract and first_contract.date_start:
                hire_date = first_contract.date_start 
                user.x_employee_first_contract_date = hire_date # Se asigna la fecha
                
                # Condición clave: el mes de contratación debe ser el mes actual
                # Y el año actual debe ser mayor que el año de contratación (para celebrar a partir del 1er aniversario)
                if hire_date.month == current_month and current_year > hire_date.year:
                    user.x_employee_years_in_company = current_year - hire_date.year
                    _logger.debug(f"Aniversario - ¡CUMPLE!: Usuario {user.name}, Años: {user.x_employee_years_in_company}, Fecha Contrato: {hire_date}")
                else:
                    _logger.debug(f"Aniversario - NO CUMPLE ESTE MES/AÑO: Usuario {user.name}, Fecha Contrato: {hire_date}, Mes Contrato: {hire_date.month}, Mes Actual: {current_month}, Año Contrato: {hire_date.year}, Año Actual: {current_year}")
            else:
                _logger.debug(f"Aniversario - Sin contrato válido para: Usuario {user.name}")

    @api.depends_context('uid')
    def _compute_days_in_company(self):
        today = date.today()
        # Buscamos los empleados asociados a los usuarios actuales
        employees = self.env['hr.employee'].search([('user_id', 'in', self.ids)])
        employee_map = {employee.user_id.id: employee for employee in employees}

        for user in self:
            user.x_days_in_company = 0 # Valor por defecto

            employee = employee_map.get(user.id)
            if not employee:
                continue

            # Buscamos el primer contrato del empleado
            first_contract = self.env['hr.contract'].search([
                ('employee_id', '=', employee.id),
                ('date_start', '!=', False),
                ('date_start', '<=', today)
            ], order='date_start asc', limit=1)

            if first_contract:
                delta = today - first_contract.date_start
                user.x_days_in_company = delta.days 