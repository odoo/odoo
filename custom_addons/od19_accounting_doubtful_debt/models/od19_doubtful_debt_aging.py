from odoo import api, fields, models
from odoo.exceptions import ValidationError


class Od19DoubtfulDebtAgingLine(models.Model):
    _name = "od19.doubtful.debt.aging.line"
    _description = "Doubtful Debt Aging Bucket"
    _order = "company_id, sequence, from_days"

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    from_days = fields.Integer(
        default=0,
        required=True,
        help="อายุหนี้ขั้นต่ำของช่วงนี้ (วัน)",
    )
    to_days = fields.Integer(
        default=0,
        help="อายุหนี้ขั้นสูงของช่วงนี้ (วัน) — 0 = ไม่จำกัด (ช่วงสุดท้าย)",
    )
    provision_rate = fields.Float(
        string="Provision Rate (%)",
        digits=(5, 2),
        help="อัตราการตั้งค่าเผื่อหนี้สงสัยจะสูญของช่วงอายุหนี้นี้",
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        ondelete="cascade",
    )

    @api.constrains("from_days", "to_days", "provision_rate")
    def _check_bucket(self):
        for line in self:
            if line.from_days < 0:
                raise ValidationError("อายุหนี้ขั้นต่ำต้องไม่ติดลบ")
            if line.to_days and line.to_days < line.from_days:
                raise ValidationError(
                    "อายุหนี้ขั้นสูง (%s) ต้องไม่น้อยกว่าขั้นต่ำ (%s)"
                    % (line.to_days, line.from_days)
                )
            if line.provision_rate < 0 or line.provision_rate > 100:
                raise ValidationError("อัตราการตั้งเผื่อต้องอยู่ระหว่าง 0 ถึง 100 เปอร์เซ็นต์")

    def _od19_match(self, days):
        """Return True when ``days`` (age of the debt) falls in this bucket."""
        self.ensure_one()
        return days >= self.from_days and (not self.to_days or days <= self.to_days)
