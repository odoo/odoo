
for code in ['NUR101-SEC01', 'NUR201-SEC01', 'NUR102-SEC01', 'NUR103-SEC01', 'CHEM101-SEC01']:
    sec = env['university.class.section'].search([('name', '=', code)], limit=1)
    sem = sec.semester_id
    ay = sec.academic_year_id
    print(f'{code}: Semester={sem.name} ({sem.date_start} to {sem.date_end}), AcademicYear={ay.name}')
