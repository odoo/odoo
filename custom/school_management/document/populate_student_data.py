import xmlrpc.client

common = xmlrpc.client.ServerProxy('http://localhost:8070/xmlrpc/2/common')
uid = common.authenticate('odoo', 'admin', 'admin', {})
models = xmlrpc.client.ServerProxy('http://localhost:8070/xmlrpc/2/object')

student_id = 6
semester_id = 3084
year_id = 3508

print("Logged in as admin uid:", uid)

# 1. Course Registration
existing_reg = models.execute_kw('odoo', uid, 'admin', 'university.course.registration', 'search', [[('student_id', '=', student_id)]])
if not existing_reg:
    reg_id = models.execute_kw('odoo', uid, 'admin', 'university.course.registration', 'create', [{
        'student_id': student_id,
        'semester_id': semester_id,
        'academic_year_id': year_id,
        'notes': 'Fall 2026 Regular Semester Course Registration (Add/Drop Period)',
        'state': 'submitted',
        'line_ids': [
            (0, 0, {
                'action_type': 'add',
                'section_id': 2118,
                'validation_status': 'valid',
                'validation_message': 'Eligible / Clear',
            }),
            (0, 0, {
                'action_type': 'add',
                'section_id': 2119,
                'validation_status': 'valid',
                'validation_message': 'Eligible / Clear',
            }),
            (0, 0, {
                'action_type': 'add',
                'section_id': 2241,
                'validation_status': 'valid',
                'validation_message': 'Eligible / Clear',
            }),
        ]
    }])
    print("Created Course Registration ID:", reg_id)
else:
    print("Course Registration already exists:", existing_reg)

# 2. Service Requests
existing_sr = models.execute_kw('odoo', uid, 'admin', 'university.service.request', 'search', [[('student_id', '=', student_id)]])
if not existing_sr:
    sr1 = models.execute_kw('odoo', uid, 'admin', 'university.service.request', 'create', [{
        'student_id': student_id,
        'request_type': 'enrollment_cert',
        'title': 'Official Certificate of Enrollment for Visa Renewal',
        'description': 'Required by the Royal Embassy of Japan for international clinical exchange visa application.',
        'copies': 2,
        'delivery_method': 'digital',
        'state': 'completed',
        'staff_notes': 'Certificate signed and officially sealed by the Office of the Registrar. PDF available in portal.'
    }])
    sr2 = models.execute_kw('odoo', uid, 'admin', 'university.service.request', 'create', [{
        'student_id': student_id,
        'request_type': 'recommendation_letter',
        'title': 'Academic Recommendation Letter - Clinical Internship',
        'description': 'Required for submission to Calmette National Hospital clinical residency program.',
        'copies': 1,
        'delivery_method': 'campus_pickup',
        'state': 'in_review',
        'staff_notes': 'Forwarded to Dean of Nursing & Public Health for faculty endorsement.'
    }])
    sr3 = models.execute_kw('odoo', uid, 'admin', 'university.service.request', 'create', [{
        'student_id': student_id,
        'request_type': 'id_card_replacement',
        'title': 'Replacement of Damaged RFID Student ID Card',
        'description': 'Physical chip cracked, campus library and lab turnstile doors fail to read.',
        'copies': 1,
        'delivery_method': 'campus_pickup',
        'state': 'approved',
        'staff_notes': 'Payment verified ($5.00). New smartcard printed, available for pickup at Counter 2.'
    }])
    print("Created Service Requests:", sr1, sr2, sr3)
else:
    print("Service Requests already exist:", existing_sr)

# 3. Profile Change Request
existing_cr = models.execute_kw('odoo', uid, 'admin', 'university.student.change.request', 'search', [[('student_id', '=', student_id)]])
if not existing_cr:
    cr_id = models.execute_kw('odoo', uid, 'admin', 'university.student.change.request', 'create', [{
        'student_id': student_id,
        'proposed_name': 'Hannah Abbott',
        'proposed_name_khmer': 'ហាណា អាបុត',
        'proposed_phone': '+855 12 778 899',
        'proposed_emergency_name': 'Alice Abbott (Mother)',
        'proposed_emergency_phone': '+855 12 889 900',
        'reason': 'Updating official Khmer transliteration for Ministry degree accreditation and emergency contact.',
        'state': 'pending',
    }])
    print("Created Profile Change Request ID:", cr_id)
else:
    print("Profile Change Request already exists:", existing_cr)

# 4. Course Evaluations
existing_ev = models.execute_kw('odoo', uid, 'admin', 'university.course.evaluation', 'search', [[('student_id', '=', student_id)]])
if not existing_ev:
    ev1 = models.execute_kw('odoo', uid, 'admin', 'university.course.evaluation', 'create', [{
        'student_id': student_id,
        'section_id': 2118,
        'rating_content': '5',
        'rating_teaching': '5',
        'rating_punctuality': '5',
        'rating_grading': '4',
        'rating_facilities': '5',
        'comments': 'Outstanding instruction. Clinical demonstrations in the anatomy lab were exceptionally well organized.',
        'strengths': 'Practical hospital case studies, clear anatomical models, and highly engaging lecture slides.',
        'improvements': 'Provide additional online quiz self-assessments before midterm examination.',
        'state': 'submitted',
    }])
    ev2 = models.execute_kw('odoo', uid, 'admin', 'university.course.evaluation', 'create', [{
        'student_id': student_id,
        'section_id': 2241,
        'rating_content': '4',
        'rating_teaching': '5',
        'rating_punctuality': '4',
        'rating_grading': '5',
        'rating_facilities': '4',
        'comments': 'The clinical skills lab provided great hands-on practice for vital sign assessment and sterile techniques.',
        'strengths': 'Passionate lecturer, excellent feedback on practical clinical examinations.',
        'improvements': 'Extend lab practice hours during weekends.',
        'state': 'submitted',
    }])
    print("Created Course Evaluations:", ev1, ev2)
else:
    print("Course Evaluations already exist:", existing_ev)

print("Data population complete!")
