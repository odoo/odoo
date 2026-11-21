import sys
sys.path.insert(0, r"C:\Odoo\odoo")
import odoo
from odoo.modules.registry import Registry
from odoo import api, SUPERUSER_ID

config_file = r"C:\Odoo\odoo\odoo.conf"
odoo.tools.config.parse_config(["-c", config_file])

registry = Registry("odoo")
with registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})
    
    # 1. Check company name and logo
    main_company = env.ref("base.main_company")
    print(f"[TEST 1] Main Company Name: '{main_company.name}' (Expected: 'Sample University')")
    assert main_company.name == "Sample University", f"Expected 'Sample University', got '{main_company.name}'"

    # 2. Check grade scale and lines
    scale = env["university.grade.scale"].search([], limit=1)
    print(f"[TEST 2] Grade Scale: {scale.name}")
    for l in scale.line_ids.sorted("min_score", reverse=True):
        print(f"   Grade {l.name}: score {l.min_score}-{l.max_score}, pt {l.grade_point}, honors {l.honors_grade_point}, passing {l.is_passing}")

    # Set honors grade points on the scale for testing weighted GPA
    honors_map = {"A+": 5.0, "A": 5.0, "A-": 4.7, "B+": 4.3, "B": 4.0, "B-": 3.7, "C+": 3.3, "C": 3.0, "C-": 2.7, "D": 2.0, "F": 0.0}
    for l in scale.line_ids:
        if l.name in honors_map and not l.honors_grade_point:
            l.honors_grade_point = honors_map[l.name]

    # 3. Create / find test students:
    # Student A: 4.00 GPA with 12 credits -> Dean's List
    # Student B: 3.40 GPA with 12 credits -> Good Standing (No Dean's List)
    # Student C: 4.00 GPA with 6 credits -> Good Standing (Credit threshold not met)
    dept = env["university.department"].search([], limit=1)
    prog = env["university.program"].search([], limit=1)
    year = env["university.academic.year"].search([("state", "=", "running")], limit=1) or env["university.academic.year"].search([], limit=1)
    sem = env["university.semester"].search([("academic_year_id", "=", year.id)], limit=1) or env["university.semester"].search([], limit=1)

    subj1 = env["university.subject"].search([], limit=1)
    subj2 = env["university.subject"].search([("id", "!=", subj1.id)], limit=1)
    subj3 = env["university.subject"].search([("id", "not in", [subj1.id, subj2.id])], limit=1)
    subj4 = env["university.subject"].search([("id", "not in", [subj1.id, subj2.id, subj3.id])], limit=1)

    # Student A
    student_a = env["university.student"].create({
        "name": "Test Student 4.0-12Cr",
        "student_id": "STD-TEST-400",
        "gender": "male",
        "program_id": prog.id,
    })
    card_a = env["university.report.card"].create({
        "student_id": student_a.id,
        "academic_year_id": year.id,
        "semester_id": sem.id,
        "grade_scale_id": scale.id,
        "state": "approved",
    })
    # 4 subjects of 3 credits each with A (4.0) -> 12 credits, GPA 4.0
    for s in [subj1, subj2, subj3, subj4]:
        env["university.report.card.line"].create({
            "report_card_id": card_a.id,
            "subject_id": s.id,
            "credits": 3,
            "final_score": 95.0,
            "grade": "A",
            "grade_point": 4.0,
            "is_passing": True,
        })
    card_a._compute_gpa()
    print(f"[TEST 3A] Student A Report Card GPA: {card_a.gpa}, Credits: {card_a.passed_credits}, Standing: {card_a.academic_standing}")
    assert card_a.academic_standing == "dean_list", f"Expected dean_list, got {card_a.academic_standing}"

    # Student B: 3.4 GPA with 12 credits
    student_b = env["university.student"].create({
        "name": "Test Student 3.4-12Cr",
        "student_id": "STD-TEST-340",
        "gender": "female",
        "program_id": prog.id,
    })
    card_b = env["university.report.card"].create({
        "student_id": student_b.id,
        "academic_year_id": year.id,
        "semester_id": sem.id,
        "grade_scale_id": scale.id,
        "state": "approved",
    })
    # 4 subjects of 3 credits: three with 3.3 (B+), one with 3.7 (A-) -> avg 3.4
    for s, gp, gr in [(subj1, 3.3, "B+"), (subj2, 3.3, "B+"), (subj3, 3.3, "B+"), (subj4, 3.7, "A-")]:
        env["university.report.card.line"].create({
            "report_card_id": card_b.id,
            "subject_id": s.id,
            "credits": 3,
            "final_score": 82.0,
            "grade": gr,
            "grade_point": gp,
            "is_passing": True,
        })
    card_b._compute_gpa()
    print(f"[TEST 3B] Student B Report Card GPA: {card_b.gpa}, Credits: {card_b.passed_credits}, Standing: {card_b.academic_standing}")
    assert card_b.academic_standing == "good", f"Expected good (no dean list), got {card_b.academic_standing}"

    # Student C: 4.0 GPA with only 6 credits (< 12 min credits)
    student_c = env["university.student"].create({
        "name": "Test Student 4.0-6Cr",
        "student_id": "STD-TEST-400-6CR",
        "gender": False, # test empty gender
        "program_id": prog.id,
    })
    card_c = env["university.report.card"].create({
        "student_id": student_c.id,
        "academic_year_id": year.id,
        "semester_id": sem.id,
        "grade_scale_id": scale.id,
        "state": "approved",
    })
    for s in [subj1, subj2]:
        env["university.report.card.line"].create({
            "report_card_id": card_c.id,
            "subject_id": s.id,
            "credits": 3,
            "final_score": 95.0,
            "grade": "A",
            "grade_point": 4.0,
            "is_passing": True,
        })
    card_c._compute_gpa()
    print(f"[TEST 3C] Student C (4.0 GPA, 6 Cr) Standing: {card_c.academic_standing}")
    assert card_c.academic_standing == "good", f"Expected good (below 12 credits), got {card_c.academic_standing}"

    # 4. Create transcripts for testing PDF/HTML rendering
    # Transcript 1: Approved transcript for Student A (Dean's List, 4.0, 12 credits)
    transcript_a = env["university.transcript"].create({
        "student_id": student_a.id,
        "verification_code": "VERIF-TEST-A123",
    })
    transcript_a.action_generate_lines()
    transcript_a.action_approve()
    print(f"[TEST 4A] Transcript A Standing: {transcript_a.academic_standing}, Cumulative GPA: {transcript_a.cumulative_gpa}")
    assert transcript_a.academic_standing == "dean_list"

    # Transcript 2: Draft transcript for Student B (Draft watermark, 3.4 GPA, No Dean's List)
    transcript_b = env["university.transcript"].create({
        "student_id": student_b.id,
        "verification_code": "VERIF-TEST-B456",
    })
    transcript_b.action_generate_lines()
    transcript_b.state = "draft"
    print(f"[TEST 4B] Transcript B Standing: {transcript_b.academic_standing}, Cumulative GPA: {transcript_b.cumulative_gpa}")
    assert transcript_b.academic_standing == "good"

    # Transcript 3: Student C (No gender, 6 credits)
    transcript_c = env["university.transcript"].create({
        "student_id": student_c.id,
        "state": "generated",
        "verification_code": "VERIF-TEST-C789",
    })
    transcript_c.action_generate_lines()

    # 5. Render HTML and verify all requirements
    report_action = env.ref("school_management.action_report_university_transcript")
    
    # Render Transcript A
    html_a = report_action._render_qweb_html("school_management.action_report_university_transcript", [transcript_a.id])[0].decode("utf-8")
    assert "Sample University" in html_a, "Missing 'Sample University' in Transcript A"
    assert "Harvard" not in html_a, "'Harvard' found in Transcript A!"
    assert "DRAFT" not in html_a, "DRAFT watermark should NOT be in approved transcript"
    assert "Dean's List" in html_a, "Dean's List should be in Transcript A"
    assert "/ 5.00" in html_a, "Weighted denominator / 5.00 should be in Transcript A"
    assert "font-family: inherit; letter-spacing: 1px;" in html_a, "Verification styling missing"
    assert "SAMPLE DOCUMENT - NOT AN OFFICIAL RECORD" in html_a, "Sample document notice missing"
    assert "Gender:" in html_a, "Gender should be present for Student A"

    # Render Transcript B (Draft)
    html_b = report_action._render_qweb_html("school_management.action_report_university_transcript", [transcript_b.id])[0].decode("utf-8")
    assert "DRAFT" in html_b, "DRAFT watermark SHOULD be present in draft transcript"
    assert "Dean's List" not in html_b, "Dean's List should NOT be in Transcript B (GPA 3.4)"
    assert "Good Standing" in html_b, "Good Standing should be in Transcript B"

    # Render Transcript C (Empty Gender)
    html_c = report_action._render_qweb_html("school_management.action_report_university_transcript", [transcript_c.id])[0].decode("utf-8")
    # Gender row should be hidden when empty
    assert "Gender:" not in html_c, "Gender row should be hidden when student gender is empty!"

    # 6. Render PDF
    pdf_a, _ = report_action._render_qweb_pdf("school_management.action_report_university_transcript", [transcript_a.id])
    print(f"[TEST 5] PDF for Transcript A generated successfully! Size: {len(pdf_a)} bytes")
    with open("scratch/transcript_approved.pdf", "wb") as f:
        f.write(pdf_a)

    pdf_b, _ = report_action._render_qweb_pdf("school_management.action_report_university_transcript", [transcript_b.id])
    print(f"[TEST 6] PDF for Transcript B (Draft) generated successfully! Size: {len(pdf_b)} bytes")
    with open("scratch/transcript_draft.pdf", "wb") as f:
        f.write(pdf_b)

    # 7. Test Program min_graduation_grade_id
    passing_grade_line = scale.line_ids.filtered(lambda l: l.is_passing and l.name == "C")[:1]
    if passing_grade_line:
        prog.min_graduation_grade_id = passing_grade_line.id
        parser_vals = env["report.school_management.report_university_transcript_document"]._get_report_values([transcript_a.id])
        print(f"[TEST 7] Program min graduation grade set to C: {parser_vals['passing_line'].name}")
        assert parser_vals["passing_line"].id == passing_grade_line.id

    cr.rollback()
    print("ALL TESTS PASSED WITH 100% SUCCESS!")
