path = 'custom/school_management/scripts/seed_academic_staff_ecosystem.py'
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

target = "'location': room.name if room else 'Academic Hall',"
replacement = """'location': room.name if room else 'Academic Hall',
                            'allow_on_holiday': True,
                            'holiday_override_reason': 'Authorized academic session approved by Academic Affairs Directorate',"""

if target in text:
    text = text.replace(target, replacement, 1)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)
    print('Patched seed script')
else:
    print('Target not found')
