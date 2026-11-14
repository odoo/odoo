model_file = "custom/school_management/models/timetable.py"
with open(model_file, "r", encoding="utf-8") as f:
    code = f.read()

old_compute = """    @api.depends("teacher_id")
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

new_compute = """    @api.depends("teacher_id")
    def _compute_resource_id(self):
        for slot in self:
            if slot.teacher_id and hasattr(slot.teacher_id, "resource_id") and slot.teacher_id.resource_id:
                slot.resource_id = slot.teacher_id.resource_id.id
            elif not slot.resource_id:
                slot.resource_id = False"""

if old_compute in code:
    code = code.replace(old_compute, new_compute, 1)
    with open(model_file, "w", encoding="utf-8") as f:
        f.write(code)
    print("Safely replaced _compute_resource_id in timetable.py")
else:
    print("Warning: old_compute not found")
