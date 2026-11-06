import os

file_path = os.path.join(os.path.dirname(__file__), "..", "models", "teacher.py")
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = """    advisee_count = fields.Integer(
        string="Advisee Count",
        compute="_compute_advisee_count",
    )"""

fields_to_add = """    advisee_count = fields.Integer(
        string="Advisee Count",
        compute="_compute_advisee_count",
    )

    # Academic Credentials & Employment Documentation
    resume_file = fields.Binary(string="Curriculum Vitae (CV)", attachment=True)
    resume_filename = fields.Char(string="CV Filename")
    degree_file = fields.Binary(string="Highest Degree & Transcripts", attachment=True)
    degree_filename = fields.Char(string="Degree Filename")
    contract_file = fields.Binary(string="Employment Contract", attachment=True)
    contract_filename = fields.Char(string="Contract Filename")
    id_card_file = fields.Binary(string="National ID / Passport", attachment=True)
    id_card_filename = fields.Char(string="ID Document Filename")
    doc_verification_status = fields.Selection(
        [
            ("verified", "Verified & Authenticated"),
            ("pending", "Pending Verification"),
            ("requires_update", "Requires Update"),
        ],
        string="Credentials Status",
        default="verified",
        tracking=True,
    )
    verification_date = fields.Date(string="Verified On")
    verified_by = fields.Many2one("res.users", string="Verified By")
    research_interests = fields.Text(string="Research Interests & Expertise")
    publications_summary = fields.Text(string="Key Publications & Research Projects")
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "university_teacher_attachment_rel",
        "teacher_id",
        "attachment_id",
        string="Additional Documents & Certifications",
    )"""

if target in content and "resume_file = fields.Binary" not in content:
    content = content.replace(target, fields_to_add, 1)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("teacher.py patched successfully!")
else:
    print("Already patched or target not found.")
