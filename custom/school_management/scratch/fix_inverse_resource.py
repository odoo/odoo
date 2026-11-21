model_file = "custom/school_management/models/timetable.py"
with open(model_file, "r", encoding="utf-8") as f:
    text = f.read()

old_inverse = """    def _inverse_resource_id(self):
        for slot in self:
            if slot.resource_id and slot.resource_id.teacher_id:
                slot.teacher_id = slot.resource_id.teacher_id.id
            elif not slot.resource_id:
                slot.teacher_id = False"""

new_inverse = """    def _inverse_resource_id(self):
        for slot in self:
            if slot.resource_id and slot.resource_id.teacher_id:
                if slot.teacher_id != slot.resource_id.teacher_id:
                    slot.teacher_id = slot.resource_id.teacher_id.id
            elif not slot.resource_id and slot.teacher_id:
                slot.teacher_id = False"""

if old_inverse in text:
    text = text.replace(old_inverse, new_inverse, 1)
    with open(model_file, "w", encoding="utf-8") as f:
        f.write(text)
    print("Updated _inverse_resource_id in timetable.py")
