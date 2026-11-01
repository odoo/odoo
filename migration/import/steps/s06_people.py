# -*- coding: utf-8 -*-
"""s06_people — บุคลากร: พนักงาน / แผนก / ผู้ใช้ / กลุ่ม"""
import common


def run(stats):
    common.log("s06_people: (scaffold) — ยังไม่ได้นำเข้าจริง")

    # TODO(แผนก): นำเข้า hr.department ก่อน (ต้องมีแผนกก่อนพนักงาน)
    #   ตั้ง parent_id ให้ตรงโครงสร้างองค์กร
    #
    # TODO(พนักงาน): นำเข้า hr.employee (name, department_id, job_title, work_email, ...)
    #   โดย map แผนกจากขั้นตอนก่อนหน้า
    #
    # TODO(ผู้ใช้): สร้าง res.users สำหรับผู้ที่ต้องใช้งาน (login, group_ids)
    #   *** ห้ามตั้งรหัสผ่านเป็นค่าคงที่ *** ให้ส่งอีเมลรีเซ็ตรหัสผ่านหรือตั้งเป็น
    #   ขั้นตอนแยกที่ปลอดภัย
    #
    # TODO(กลุ่ม): map สิทธิ์การเข้าถึง (res.groups) ให้ตรงกับบทบาทในระบบเดิม
    stats.skipped += 1
