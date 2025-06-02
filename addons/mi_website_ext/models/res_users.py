# En mi_website_ext/models/res_users.py
from odoo import models, fields, api
from datetime import date 
from dateutil.relativedelta import relativedelta # Para cálculos de mes
from odoo.tools.misc import format_date # Para formateo de fecha localizado
import logging
_logger = logging.getLogger(__name__)
# from datetime import datetime # Descomenta si necesitas comparar con campos Datetime
# from odoo.tools import date_utils # Útil para operaciones con fechas

class Users(models.Model):
    _inherit = 'res.users'
    
    x_days_until_vacation_display = fields.Char(
        string="Días Para Próximas Vacaciones",
        compute='_compute_days_until_next_vacation',
        store=False 
    )

    # Asumo que ya tienes este campo para las horas de permiso o lo añadirás después
    x_available_remunerated_permission_hours = fields.Char(
        string="Horas de Permiso Remunerado Disponibles", 
        compute='_compute_remunerated_permission_hours',
        store=False
    )

   # --- Nuevos campos para la lógica de Aniversario ---
    # Guardamos la fecha de inicio del primer contrato para usarla en QWeb
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

        # ID específico para el tipo de ausencia "Vacaciones"
        # Según tu información, el ID para "Vacaciones" en holiday_status_id es 8.
        # Es más robusto si pudieras obtener este ID a través de un XML ID si lo conoces
        # Por ejemplo: vacation_leave_type_id = self.env.ref('nombre_modulo.xml_id_del_tipo_vacacion').id
        # Pero si sabes que es 8 y es estable en tu sistema, puedes usarlo directamente.
        # ¡PRECAUCIÓN!: Usar IDs numéricos directamente puede ser frágil si cambian entre instancias de Odoo.
        # Sería mejor buscar el hr.leave.type por nombre o xml_id si es posible.
        # Ejemplo buscando por nombre (sensible a cambios de nombre o idioma si no es un campo traducible correctamente buscado):
        # vacation_leave_type = self.env['hr.leave.type'].search([('name', '=ilike', 'Vacaciones')], limit=1)
        # vacation_leave_type_id = vacation_leave_type.id if vacation_leave_type else None
        
        # Por ahora, usaremos el ID 8 que proporcionaste, pero ten en cuenta la fragilidad.
        # Una forma un poco más segura que el ID hardcodeado, si el nombre es consistente:
        vacation_leave_type = self.env['hr.leave.type'].search([('name', '=', 'Vacaciones')], limit=1) # Asume que el nombre es exactamente "Vacaciones"
        vacation_leave_type_id = vacation_leave_type.id if vacation_leave_type else None
        
        # Si el ID 8 es fijo y seguro para tu instancia:
        # vacation_leave_type_id = 8 


        if not vacation_leave_type_id:
            _logger.warning("No se pudo encontrar el tipo de ausencia 'Vacaciones'. Verifica el nombre o ID.")
            for user_no_type in self:
                user_no_type.x_days_until_vacation_display = "--"
            return

        for user in self:
            employee = HrEmployee.search([('user_id', '=', user.id)], limit=1)
            if not employee:
                user.x_days_until_vacation_display = "--"
                continue

            domain = [
                ('employee_id', '=', employee.id),
                ('state', '=', 'validate'),  # Solo ausencias aprobadas
                ('request_date_from', '>', today), # Que empiecen después de hoy
                ('holiday_status_id', '=', vacation_leave_type_id), # Solo tipo "Vacaciones"
            ]

            next_vacation = HrLeave.search(domain, order='request_date_from asc', limit=1)

            if next_vacation and next_vacation.request_date_from:
                vacation_start_date = next_vacation.request_date_from
                delta = vacation_start_date - today
                days_remaining = delta.days

                if days_remaining == 0:
                    user.x_days_until_vacation_display = "Hoy"
                elif days_remaining == 1:
                    user.x_days_until_vacation_display = "Mañana"
                else:
                    user.x_days_until_vacation_display = str(days_remaining)
            else:
                user.x_days_until_vacation_display = "--"

    @api.depends_context('uid')
    def _compute_remunerated_permission_hours(self):
        monthly_allowance_hours = 8.0 
        # ID específico para el tipo de ausencia "Permiso remunerado" es 6
        # Es más robusto buscarlo por XML ID o por nombre si el ID numérico no es 100% estable.
        # Intentemos por nombre primero, y si no, usamos el ID 6 como fallback (con advertencia).
        permission_leave_type = self.env['hr.leave.type'].search([
            ('name', '=', 'Solicitud de permiso') # Buscar por el nombre exacto
        ], limit=1)
        
        permission_leave_type_id = None
        if permission_leave_type:
            permission_leave_type_id = permission_leave_type.id
        elif self.env['hr.leave.type'].browse(6).exists(): # Verificar si el ID 6 existe como fallback
            # Solo usar el ID 6 directamente si la búsqueda por nombre falla Y sabes que el ID 6 es correcto
            # y estable en tu instancia específica.
            _logger.warning("No se encontró 'Solicitud de permiso' por nombre, usando ID 6 como fallback. Es preferible usar XML ID o asegurar el nombre.")
            permission_leave_type_id = 6
        else:
            _logger.error("Tipo de ausencia 'Solicitud de permiso' (ID 6 o por nombre) no encontrado. Verifica la configuración de Tipos de Ausencia en RRHH.")
            for user_no_type in self:
                user_no_type.x_available_remunerated_permission_hours = "Error Conf."
            return

        today = fields.Date.context_today(self)
        first_day_current_month = today.replace(day=1)
        last_day_current_month = (today.replace(day=1) + relativedelta(months=1) - relativedelta(days=1))
        
        HrEmployee = self.env['hr.employee']
        HrLeave = self.env['hr.leave']

        for user in self:
            employee = HrEmployee.search([('user_id', '=', user.id)], limit=1)
            if not employee:
                user.x_available_remunerated_permission_hours = "--"
                continue

            domain = [
                ('employee_id', '=', employee.id),
                ('holiday_status_id', '=', permission_leave_type_id),
                ('state', '=', 'validate'), # Solo ausencias aprobadas
                # Filtrar por ausencias que ocurran total o parcialmente en el mes actual
                ('request_date_from', '<=', last_day_current_month),
                ('request_date_to', '>=', first_day_current_month),
            ]
            
            approved_permissions = HrLeave.search(domain)

            hours_taken_this_month = 0.0
            for leave in approved_permissions:
                # Prioriza el uso de campos numéricos si están disponibles en tu versión de Odoo
                # como number_of_hours_display (Odoo 16+) o number_of_days
                if 'number_of_hours_display' in leave and leave.request_unit_hours: # Odoo 16+ y si se piden en horas
                    hours_taken_this_month += leave.number_of_hours_display
                elif 'number_of_days' in leave: # Para versiones donde se usa días
                    # Necesitas saber cómo se cuentan los días parciales.
                    # Aquí asumimos que number_of_days es correcto y lo multiplicamos por horas/día del empleado.
                    hours_per_day = employee.resource_calendar_id.hours_per_day or 8.0
                    hours_taken_this_month += leave.number_of_days * hours_per_day
                else:
                    # Fallback a parsear duration_display si los campos numéricos no están o no aplican
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
            # Formatear para mostrar solo el número entero y la "H"
            user.x_available_remunerated_permission_hours = f"{max(0, remaining_hours):.0f}H"


     # Método de cómputo para los detalles del aniversario
    
    @api.depends_context('uid') # O simplemente @api.depends() si no necesitas el contexto específico
    def _compute_anniversary_details(self):
        today = fields.Date.context_today(self) # Fecha actual correcta
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