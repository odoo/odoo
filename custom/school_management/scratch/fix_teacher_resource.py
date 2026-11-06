import os

# 1. Update _compute_resource_id in timetable.py
model_file = "custom/school_management/models/timetable.py"
with open(model_file, "r", encoding="utf-8") as f:
    code = f.read()

old_compute = """    @api.depends("teacher_id")
    def _compute_resource_id(self):
        for slot in self:
            if slot.teacher_id:
                slot.resource_id = slot.teacher_id._get_or_create_resource().id
            elif not slot.resource_id:
                slot.resource_id = False"""

new_compute = """    @api.depends("teacher_id")
    def _compute_resource_id(self):
        Resource = self.env["resource.resource"].sudo()
        for slot in self:
            if slot.teacher_id:
                res = Resource.search([("teacher_id", "=", slot.teacher_id.id)], limit=1)
                if not res:
                    res = Resource.create({
                        "name": slot.teacher_id.name,
                        "resource_type": "user",
                        "user_id": slot.teacher_id.user_id.id if slot.teacher_id.user_id else False,
                        "teacher_id": slot.teacher_id.id,
                        "weekly_capacity_hours": 35.0,
                    })
                slot.resource_id = res.id
            elif not slot.resource_id:
                slot.resource_id = False"""

if old_compute in code:
    code = code.replace(old_compute, new_compute, 1)

# Also in get_gantt_data:
code = code.replace("t._get_or_create_resource()", """res = Resource.search([("teacher_id", "=", t.id)], limit=1)
            if not res:
                Resource.create({
                    "name": t.name,
                    "resource_type": "user",
                    "user_id": t.user_id.id if t.user_id else False,
                    "teacher_id": t.id,
                    "weekly_capacity_hours": 35.0,
                })""")

with open(model_file, "w", encoding="utf-8") as f:
    f.write(code)
print("Updated _compute_resource_id in timetable.py")

# 2. Add resource_id and _get_or_create_resource directly to teacher.py
teacher_file = "custom/school_management/models/teacher.py"
with open(teacher_file, "r", encoding="utf-8") as f:
    t_code = f.read()

if "resource_id = fields.Many2one(\"resource.resource\"" not in t_code:
    target_pos = t_code.find("class UniversityTeacher(models.Model):")
    if target_pos != -1:
        # Find next line after docstring or class def
        insert_marker = '    name = fields.Char('
        t_code = t_code.replace(
            insert_marker,
            '    resource_id = fields.Many2one("resource.resource", string="Resource", copy=False, index=True)\n' + insert_marker,
            1
        )
        methods = '''
    def _get_or_create_resource(self):
        self.ensure_one()
        Resource = self.env["resource.resource"].sudo()
        if self.resource_id:
            return self.resource_id
        res = Resource.search([("teacher_id", "=", self.id)], limit=1)
        if not res:
            res = Resource.create({
                "name": self.name,
                "resource_type": "user",
                "user_id": self.user_id.id if self.user_id else False,
                "teacher_id": self.id,
                "weekly_capacity_hours": 35.0,
            })
        self.resource_id = res.id
        return res
'''
        t_code = t_code + "\n" + methods
        with open(teacher_file, "w", encoding="utf-8") as f:
            f.write(t_code)
        print("Updated teacher.py with resource_id and _get_or_create_resource")
