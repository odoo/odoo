# -*- coding: utf-8 -*-
"""ตัวช่วยกลางของชุดสร้างข้อมูลตัวอย่าง Odoo 19 (เครื่องมือภายนอก ไม่ใช่โมดูล Odoo)

หลักการ:
    * เขียนข้อมูลผ่าน ORM เท่านั้น
    * ทุก record ผูก External ID รูปแบบ __seed19__.<model>.<key> -> รันซ้ำได้ไม่เกิดข้อมูลซ้ำ
    * ถ้า model/field ไม่มีในฐานข้อมูล จะข้ามพร้อม log (ไม่ทำให้ทั้งชุดล้ม)
"""
import os
import traceback

from odoo import fields as odoo_fields

MODULE_PREFIX = '__seed19__'
DRY_RUN = os.environ.get('SEED_DRY_RUN', '') == '1'


class Ctx:
    """บริบทที่ส่งต่อให้ทุก section (env ของ Odoo + state ที่ใช้ร่วมกัน)."""

    def __init__(self, env):
        self.env = env
        self.state = {}
        self.created = 0
        self.updated = 0
        self.skipped = 0
        self.errors = []
        self._step = 'seed'

    # ------------------------------------------------------------------ log
    def step(self, name, desc=''):
        self._step = name
        print("\n----- [%s] %s -----" % (name, desc))

    def log(self, msg):
        print("  [%s] %s" % (self._step, msg))

    def warn(self, msg):
        print("  [%s][WARN] %s" % (self._step, msg))

    # -------------------------------------------------------------- helpers
    def has(self, model):
        """ตรวจว่ามีโมเดลนี้ใน registry หรือไม่."""
        return model in self.env

    def fields(self, model):
        return self.env[model]._fields if self.has(model) else {}

    def xmlid(self, model, key):
        return '%s.%s.%s' % (MODULE_PREFIX, model.replace('.', '_'), key)

    def get(self, model, key):
        """อ่าน record ที่ seed ไว้ก่อนหน้า (คืน empty recordset ถ้าไม่มี)."""
        if not self.has(model):
            return self.env['base'].browse()
        rid = self.env['ir.model.data']._xmlid_to_res_id(
            self.xmlid(model, key), raise_if_not_found=False)
        return self.env[model].browse(rid) if rid else self.env[model].browse()

    def find(self, model, domain, limit=1, order=None):
        if not self.has(model):
            return self.env['base'].browse()
        return self.env[model].search(domain, limit=limit, order=order)

    def find_or_create(self, model, domain, vals, key=None):
        """หา record ตาม domain ถ้าไม่พบจึงสร้าง (ใช้กับข้อมูล master)."""
        rec = self.find(model, domain)
        if rec:
            return rec
        if key:
            existing = self.get(model, key)
            if existing:
                return existing
        return self.upsert(model, key or ('auto-%s' % abs(hash(tuple(sorted(vals.items()))))), vals)

    def upsert(self, model, key, vals):
        """สร้างหรืออัปเดต record ตาม External ID (idempotent)."""
        if not self.has(model):
            self.skipped += 1
            self.warn("ไม่มีโมเดล %s — ข้าม (%s)" % (model, key))
            return self.env['base'].browse()

        if DRY_RUN:
            self.skipped += 1
            self.log("[DRY-RUN] %s/%s" % (model, key))
            return self.env[model].browse()

        vals = self._clean(model, vals)
        xmlid = self.xmlid(model, key)
        existing_id = self.env['ir.model.data']._xmlid_to_res_id(xmlid, raise_if_not_found=False)
        try:
            # ใช้ savepoint เพื่อให้ความล้มเหลวของ record เดียวไม่ล้างงานที่ทำไปแล้วทั้ง transaction
            with self.env.cr.savepoint():
                if existing_id:
                    rec = self.env[model].browse(existing_id)
                    changed = self._changed(model, rec, vals)
                    if changed:
                        rec.write(changed)
                        self.updated += 1
                    else:
                        self.skipped += 1
                    return rec
                rec = self.env[model].create(vals)
                self.env['ir.model.data']._update_xmlids(
                    [{'xml_id': xmlid, 'record': rec, 'noupdate': True}], update=True)
                self.created += 1
                return rec
        except Exception as exc:  # pragma: no cover - tooling
            self.fail("%s/%s" % (model, key), exc)
            return self.env[model].browse()

    # ------------------------------------------------------------------ misc
    def _clean(self, model, vals):
        """ตัดฟิลด์ที่ไม่มีในโมเดลออก เพื่อกัน error จากความต่างของเวอร์ชัน."""
        flds = self.fields(model)
        return {k: v for k, v in vals.items() if k in flds}

    def _changed(self, model, rec, vals):
        changed = {}
        for name, value in vals.items():
            field = self.env[model]._fields.get(name)
            if field is None or field.type in ('one2many', 'many2many'):
                continue
            current = rec[name]
            if field.type == 'many2one':
                current = current.id or False
                value = value or False
            elif field.type in ('char', 'text', 'html'):
                current = current or False
                value = value or False
            elif field.type == 'date':
                # rec[name] เป็น datetime.date แต่ค่าใน vals เป็น string
                # ต้อง normalize ก่อนเทียบ ไม่งั้นจะเห็นว่า "เปลี่ยน" ทุกครั้ง
                value = odoo_fields.Date.to_date(value) if value else False
                current = current or False
            elif field.type == 'datetime':
                value = odoo_fields.Datetime.to_datetime(value) if value else False
                current = current or False
            if current != value:
                changed[name] = value
        return changed

    def fail(self, label, exc):
        txt = '%s: %s' % (label, exc)
        self.errors.append(txt)
        print("  [%s][ERROR] %s" % (self._step, txt))
        if os.environ.get('SEED_VERBOSE_ERROR') == '1':
            print(traceback.format_exc())

    def guard(self, label, fn, *args, **kwargs):
        """เรียก fn แบบมี error guard (คืนผลลัพธ์หรือ None)."""
        try:
            with self.env.cr.savepoint():
                return fn(*args, **kwargs)
        except Exception as exc:  # pragma: no cover - tooling
            self.fail(label, exc)
            return None

    # ------------------------------------------------------------ shortcuts
    @property
    def company(self):
        return self.env.company

    @property
    def thb(self):
        return self.env.ref('base.THB', raise_if_not_found=False) or self.company.currency_id

    def user_admin(self):
        return self.env.ref('base.user_admin', raise_if_not_found=False) or self.env.user

    def uom(self, name='Units'):
        return self.find('uom.uom', [('name', '=', name)])

    def journal(self, code):
        return self.find('account.journal', [('code', '=', code)])

    def account(self, code):
        return self.find('account.account', [('code', '=', code)])

    def summary(self):
        return 'created=%d updated=%d skipped=%d errors=%d' % (
            self.created, self.updated, self.skipped, len(self.errors))
