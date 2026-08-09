import io
import base64
import xlsxwriter
from odoo import models, fields, api


class MRpDrsProduction(models.Model):
    _name = 'mrp.drs.production'
    _description = 'DRS Production Report'
    _rec_name = 'output_roll_number'

    date = fields.Date(string="Date (التاريخ)", default=fields.Date.context_today)
    machine_number = fields.Selection([
        ('311', '311'),
        ('312', '312'),
    ], string="Machine (الماكينة)")
    shift = fields.Selection([
        ('first', 'First (أولي)'),
        ('second', 'Second (ثانية)'),
    ], string="Shift (الوردية)")
    time_from = fields.Float(string="Time From (الساعة من)", widget="float_time")
    time_to = fields.Float(string="Time To (إلي)", widget="float_time")

    supervisor_id = fields.Many2one('hr.employee', string="Supervisor (المشرف)",
                                    domain="[('is_drs_supervisor', '=', True)]")
    technician_ids = fields.Many2many('hr.employee', relation='mrp_drs_production_technician_rel',
                                      string="Technicians (أسماء الفنيين)", domain="[('is_drs_technician', '=', True)]")

    input_roll_number = fields.Char(string="Input Roll Number (رقم رول التغذية)")
    output_roll_number = fields.Char(string="Output Roll Number (رقم الرول بعد الرش)")
    product_code = fields.Char(string="Product Code (كود المنتج)")
    category = fields.Char(string="Category (التصنيف)")
    face = fields.Char(string="Face (الوجه)")
    thickness = fields.Float(string="Thickness (السمك)")
    length = fields.Float(string="Length (الطول)")
    final_weight = fields.Float(string="Final Weight (الوزن النهائي)")

    extruder_line_ids = fields.One2many('mrp.drs.extrusion.line', 'production_id', string="Extruder Readings")

    # Bottom Section Fields
    line_speed = fields.Float(string="Line Speed (سرعة الخط)")
    trolley_a_speed = fields.Float(string="Trolley A Speed (سرعة تروللي A)")
    trolley_b_speed = fields.Float(string="Trolley B Speed (سرعة تروللي B)")
    average_spray_weight = fields.Float(string="Avg Spray Weight (متوسط وزن الرش)")
    notes = fields.Text(string="Notes (ملاحظات / أعطال)")

    f11_weight_before = fields.Float(string="F11 Weight Before")
    f11_weight_after = fields.Float(string="F11 Weight After")
    f11_net_weight = fields.Float(string="F11 Net Weight", compute="_compute_sample_weights", store=True)

    f12_weight_before = fields.Float(string="F12 Weight Before")
    f12_weight_after = fields.Float(string="F12 Weight After")
    f12_net_weight = fields.Float(string="F12 Net Weight", compute="_compute_sample_weights", store=True)

    # Smart Analysis Fields
    weight_per_meter = fields.Float(string="Weight / Meter (وزن المتر)", compute="_compute_efficiency_metrics",
                                    store=True)
    spray_variance_percent = fields.Float(string="Spray Variance % (نسبة التفاوت)",
                                          compute="_compute_efficiency_metrics", store=True)
    has_temp_warnings = fields.Boolean(string="Temperature Warnings", compute="_compute_temp_warnings", store=True)

    @api.depends('f11_weight_before', 'f11_weight_after', 'f12_weight_before', 'f12_weight_after')
    def _compute_sample_weights(self):
        for rec in self:
            rec.f11_net_weight = rec.f11_weight_after - rec.f11_weight_before
            rec.f12_net_weight = rec.f12_weight_after - rec.f12_weight_before

    @api.depends('final_weight', 'length', 'f11_net_weight', 'f12_net_weight')
    def _compute_efficiency_metrics(self):
        for rec in self:
            if rec.length and rec.length > 0:
                rec.weight_per_meter = rec.final_weight / rec.length
            else:
                rec.weight_per_meter = 0.0

            if rec.f11_net_weight and rec.f12_net_weight:
                avg = (rec.f11_net_weight + rec.f12_net_weight) / 2
                diff = abs(rec.f11_net_weight - rec.f12_net_weight)
                rec.spray_variance_percent = (diff / avg) * 100 if avg > 0 else 0.0
            else:
                rec.spray_variance_percent = 0.0

    @api.depends('extruder_line_ids.is_temp_warning')
    def _compute_temp_warnings(self):
        for rec in self:
            rec.has_temp_warnings = any(line.is_temp_warning for line in rec.extruder_line_ids)

    @api.model
    def default_get(self, fields_list):
        res = super(MRpDrsProduction, self).default_get(fields_list)
        if 'extruder_line_ids' not in res:
            lines = []
            extruders = ['A1', 'A2', 'A3', 'A4', 'B1', 'B2', 'B3', 'B4']
            zones = ['zone5', 'zone4', 'zone3', 'zone2', 'zone1']
            for ext in extruders:
                for zone in zones:
                    lines.append((0, 0, {'extruder_name': ext, 'zone': zone}))
            res['extruder_line_ids'] = lines
        return res

    def action_export_excel(self):
        return self._generate_excel_action(self)

    def _format_float_time(self, float_val):
        if not float_val:
            return "00:00"
        hours = int(float_val)
        minutes = int(round((float_val - hours) * 60))
        return f"{hours:02d}:{minutes:02d}"

    def _generate_excel_action(self, records):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})

        fmt_title = workbook.add_format(
            {'bold': True, 'align': 'center', 'valign': 'vcenter', 'font_size': 14, 'border': 2, 'text_wrap': True})
        fmt_header_cell = workbook.add_format(
            {'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'text_wrap': True})
        fmt_label_r = workbook.add_format({'bold': True, 'align': 'right', 'valign': 'vcenter', 'font_size': 10})
        fmt_label_c = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'font_size': 10})
        fmt_cell = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1})
        fmt_cell_blue = workbook.add_format(
            {'align': 'center', 'valign': 'vcenter', 'border': 1, 'font_color': '#005b9f'})
        fmt_cell_orange = workbook.add_format(
            {'align': 'center', 'valign': 'vcenter', 'border': 1, 'font_color': '#d35400'})
        fmt_merged_ext = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})
        fmt_notes = workbook.add_format({'align': 'right', 'valign': 'top', 'text_wrap': True, 'border': 1})

        def val(x):
            return x if (x is not None and x != False and x != '') else ''

        def txt(x, default="........................"):
            return str(x) if (x is not None and x != False and x != '') else default

        for rec in records:
            sheet_name = (rec.output_roll_number or f"Roll_{rec.id}")[:31]
            ws = workbook.add_worksheet(sheet_name)

            ws.right_to_left()
            ws.set_paper(9)
            ws.fit_to_pages(1, 1)
            ws.set_margins(0.3, 0.3, 0.5, 0.5)

            ws.set_column('A:A', 8)
            ws.set_column('B:B', 12)
            ws.set_column('C:C', 10)
            ws.set_column('D:D', 8)
            ws.set_column('E:E', 12)
            ws.set_column('F:F', 14)
            ws.set_column('G:G', 12)
            ws.set_column('H:H', 2)
            ws.set_column('I:I', 8)
            ws.set_column('J:J', 12)
            ws.set_column('K:K', 10)
            ws.set_column('L:L', 8)
            ws.set_column('M:M', 12)
            ws.set_column('N:N', 14)
            ws.set_column('O:O', 12)

            ws.set_row(0, 40)
            ws.set_row(8, 30)

            ws.merge_range('A1:O1', 'DRS Roll Report\nتقرير إنتاج ماكينة الرش', fmt_title)

            mach = dict(rec._fields['machine_number'].selection).get(rec.machine_number,
                                                                     txt(rec.machine_number, '311 | 312'))
            ws.merge_range('M2:O2', f"الماكينة: {mach}", fmt_label_r)

            ws.merge_range('M3:O3', f"رقم الرول بعد الرش والتسجيل: {txt(rec.output_roll_number)}", fmt_label_r)
            ws.merge_range('A3:I3', f"رقم رول التغذية: {txt(rec.input_roll_number)}", fmt_label_r)

            ws.merge_range('M4:O4', f"كود المنتج: {txt(rec.product_code)}", fmt_label_r)
            ws.merge_range('F4:J4', f"السمك: {txt(rec.thickness, '......')}      الطول: {txt(rec.length, '......')}",
                           fmt_label_r)
            ws.merge_range('A4:D4', f"التصنيف: {txt(rec.category)}", fmt_label_r)

            ws.merge_range('M5:O5', f"الوجه: {txt(rec.face)}", fmt_label_r)
            ws.merge_range('A5:K5', f"الوزن النهائي: {txt(rec.final_weight, '..........')}      (عند نهاية رش الوجهين)",
                           fmt_label_c)

            ws.merge_range('M6:O6', f"التاريخ: {rec.date.strftime('%Y/%m/%d') if rec.date else '..../..../....'}",
                           fmt_label_r)
            time_str = f"{self._format_float_time(rec.time_from)} إلي {self._format_float_time(rec.time_to)}"
            ws.merge_range('I6:L6', f"الساعة من: {time_str}", fmt_label_r)
            shift_str = dict(rec._fields['shift'].selection).get(rec.shift, 'أولي | ثانية')
            ws.merge_range('E6:H6', f"الوردية: {shift_str}", fmt_label_r)
            ws.merge_range('A6:D6', f"المشرف: {rec.supervisor_id.name if rec.supervisor_id else txt('')}", fmt_label_r)

            techs = ', '.join(rec.technician_ids.mapped('name')) if rec.technician_ids else txt('',
                                                                                                '.......................................................')
            ws.merge_range('A7:O7', f"أسماء الفنيين الموجودين بالوردية: {techs}", fmt_label_r)

            headers = [
                (0, 'A'), (1, 'سرعة الاكسترودر'), (2, 'ضغط الهواء\n(بار)'), (3, 'الزون'),
                (4, 'ضبط درجة الحرارة'), (5, 'درجة الحرارة الفعلية'), (6, 'معدل تدفق الذوبان'),
                (8, 'B'), (9, 'سرعة الاكسترودر'), (10, 'ضغط الهواء\n(بار)'), (11, 'الزون'),
                (12, 'ضبط درجة الحرارة'), (13, 'درجة الحرارة الفعلية'), (14, 'معدل تدفق الذوبان')
            ]
            for col, text in headers:
                ws.merge_range(8, col, 9, col, text, fmt_header_cell)

            lines_dict = {}
            for line in rec.extruder_line_ids:
                lines_dict.setdefault(line.extruder_name, {})[line.zone] = line

            row_start = 10
            extruder_pairs = [('A1', 'B1'), ('A2', 'B2'), ('A3', 'B3'), ('A4', 'B4')]
            zones_order = ['zone5', 'zone4', 'zone3', 'zone2', 'zone1']

            for ext_a, ext_b in extruder_pairs:
                ws.merge_range(row_start, 0, row_start + 4, 0, f"Ext. {ext_a}", fmt_merged_ext)
                line_a_main = lines_dict.get(ext_a, {}).get('zone5')
                ws.merge_range(row_start, 1, row_start + 4, 1, val(line_a_main.extruder_speed) if line_a_main else '',
                               fmt_cell)
                ws.merge_range(row_start, 2, row_start + 4, 2, val(line_a_main.air_pressure) if line_a_main else '',
                               fmt_cell)
                ws.merge_range(row_start, 6, row_start + 4, 6, val(line_a_main.melt_flow_rate) if line_a_main else '',
                               fmt_cell)

                ws.merge_range(row_start, 8, row_start + 4, 8, f"Ext. {ext_b}", fmt_merged_ext)
                line_b_main = lines_dict.get(ext_b, {}).get('zone5')
                ws.merge_range(row_start, 9, row_start + 4, 9, val(line_b_main.extruder_speed) if line_b_main else '',
                               fmt_cell)
                ws.merge_range(row_start, 10, row_start + 4, 10, val(line_b_main.air_pressure) if line_b_main else '',
                               fmt_cell)
                ws.merge_range(row_start, 14, row_start + 4, 14, val(line_b_main.melt_flow_rate) if line_b_main else '',
                               fmt_cell)

                for i, z in enumerate(zones_order):
                    current_row = row_start + i
                    la = lines_dict.get(ext_a, {}).get(z)
                    lb = lines_dict.get(ext_b, {}).get(z)
                    z_label = f"Zone {5 - i}"

                    ws.write(current_row, 3, z_label, fmt_cell)
                    ws.write(current_row, 4, val(la.set_temperature) if la else '', fmt_cell_blue)
                    ws.write(current_row, 5, val(la.actual_temperature) if la else '', fmt_cell_orange)

                    ws.write(current_row, 11, z_label, fmt_cell)
                    ws.write(current_row, 12, val(lb.set_temperature) if lb else '', fmt_cell_blue)
                    ws.write(current_row, 13, val(lb.actual_temperature) if lb else '', fmt_cell_orange)

                row_start += 6

            r = row_start
            ws.merge_range(r, 12, r, 14, f"سرعة الخط: {txt(rec.line_speed, '..........')} متر / دقيقة", fmt_label_r)

            r += 1
            ws.merge_range(r, 12, r, 14, f"سرعة تروللي A: {txt(rec.trolley_a_speed, '..........')}", fmt_label_r)
            ws.merge_range(r, 5, r, 7, f"سرعة تروللي B: {txt(rec.trolley_b_speed, '..........')}", fmt_label_r)

            r += 1
            ws.merge_range(r, 11, r, 14, f"متوسط وزن الرش: {txt(rec.average_spray_weight, '..........')} جم/سم²",
                           fmt_label_r)
            ws.merge_range(r, 1, r, 5, 'أوزان العينات', fmt_header_cell)

            r += 1
            ws.write(r, 14, 'F11', fmt_label_r)
            ws.merge_range(r, 12, r, 13, 'عينة أول الرول', fmt_label_r)
            ws.write(r, 1, '', fmt_cell)
            ws.merge_range(r, 2, r, 3, 'F11', fmt_header_cell)
            ws.merge_range(r, 4, r, 5, 'F12', fmt_header_cell)

            r += 1
            ws.write(r, 14, 'F12', fmt_label_r)
            ws.merge_range(r, 12, r, 13, 'عينة آخر الرول', fmt_label_r)
            ws.write(r, 1, 'الوزن قبل', fmt_header_cell)
            ws.merge_range(r, 2, r, 3, val(rec.f11_weight_before), fmt_cell)
            ws.merge_range(r, 4, r, 5, val(rec.f12_weight_before), fmt_cell)

            r += 1
            ws.write(r, 1, 'الوزن بعد', fmt_header_cell)
            ws.merge_range(r, 2, r, 3, val(rec.f11_weight_after), fmt_cell)
            ws.merge_range(r, 4, r, 5, val(rec.f12_weight_after), fmt_cell)

            r += 1
            ws.write(r, 1, 'صافي وزن الرش', fmt_header_cell)
            ws.merge_range(r, 2, r, 3, val(rec.f11_net_weight), fmt_cell)
            ws.merge_range(r, 4, r, 5, val(rec.f12_net_weight), fmt_cell)

            r += 2
            ws.merge_range(r, 0, r, 14, 'ملاحظات  / أعطال خلال تشغيل  الرول:', fmt_label_r)
            r += 1
            ws.merge_range(r, 0, r + 3, 14, rec.notes or '\n\n\n', fmt_notes)

        workbook.close()
        output.seek(0)
        file_data = base64.b64encode(output.read())
        output.close()

        attachment = self.env['ir.attachment'].create({
            'name': 'DRS_Roll_Report.xlsx',
            'type': 'binary',
            'datas': file_data,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }


class MRpDrsExtrusionLine(models.Model):
    _name = 'mrp.drs.extrusion.line'
    _description = 'DRS Extrusion Zone Reading'

    production_id = fields.Many2one('mrp.drs.production', string="Production Ref", ondelete="cascade")
    extruder_name = fields.Selection([
        ('A1', 'Ext. A1'), ('A2', 'Ext. A2'), ('A3', 'Ext. A3'), ('A4', 'Ext. A4'),
        ('B1', 'Ext. B1'), ('B2', 'Ext. B2'), ('B3', 'Ext. B3'), ('B4', 'Ext. B4')
    ], string="Extruder", required=True)
    zone = fields.Selection([
        ('zone5', 'Zone 5'), ('zone4', 'Zone 4'), ('zone3', 'Zone 3'), ('zone2', 'Zone 2'), ('zone1', 'Zone 1')
    ], string="Zone", required=True)

    extruder_speed = fields.Float(string="Speed")
    air_pressure = fields.Float(string="Air Pressure")
    set_temperature = fields.Float(string="Set Temp")
    actual_temperature = fields.Float(string="Actual Temp")
    melt_flow_rate = fields.Float(string="Melt Flow Rate")

    temp_deviation = fields.Float(string="Temp Deviation", compute="_compute_temp_deviation")
    is_temp_warning = fields.Boolean(string="Warning", compute="_compute_temp_deviation", store=True)

    @api.depends('set_temperature', 'actual_temperature')
    def _compute_temp_deviation(self):
        for line in self:
            if line.set_temperature and line.actual_temperature:
                deviation = abs(line.actual_temperature - line.set_temperature)
                line.temp_deviation = deviation
                line.is_temp_warning = True if deviation > 10 else False
            else:
                line.temp_deviation = 0.0
                line.is_temp_warning = False
