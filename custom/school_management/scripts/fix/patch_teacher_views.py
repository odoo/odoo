import os

views_path = os.path.join(os.path.dirname(__file__), "..", "views", "teacher_views.xml")
with open(views_path, "r", encoding="utf-8") as f:
    content = f.read()

target = """                        <page string="Documents" name="documents_tab">
                            <group string="Administrative Notes">
                                <field name="notes" nolabel="1" placeholder="Add administrative notes, qualifications, or internal remarks..."/>
                            </group>
                        </page>"""

replacement = """                        <page string="Documents" name="documents_tab">
                            <div class="alert alert-info d-flex align-items-center mb-3" role="status">
                                <i class="fa fa-file-text-o fa-2x me-3 text-primary" title="Academic Credentials &amp; Employment Documents"/>
                                <div>
                                    <h5 class="mb-0 fw-bold">Academic Credentials &amp; Faculty Employment Files</h5>
                                    <small class="text-muted">Repository of verified academic diplomas, curriculum vitae, employment agreements, and research portfolios.</small>
                                </div>
                            </div>
                            <group string="Verification Status &amp; Compliance">
                                <group>
                                    <field name="doc_verification_status" widget="badge"
                                           decoration-success="doc_verification_status == 'verified'"
                                           decoration-warning="doc_verification_status == 'pending'"
                                           decoration-danger="doc_verification_status == 'requires_update'"/>
                                    <field name="verification_date"/>
                                </group>
                                <group>
                                    <field name="verified_by"/>
                                </group>
                            </group>
                            <group string="Primary Credentials &amp; Employment Documents">
                                <group string="Curriculum Vitae &amp; Diplomas">
                                    <field name="resume_file" filename="resume_filename" widget="binary"/>
                                    <field name="resume_filename" invisible="1"/>
                                    <field name="degree_file" filename="degree_filename" widget="binary"/>
                                    <field name="degree_filename" invisible="1"/>
                                </group>
                                <group string="Contract &amp; Identification">
                                    <field name="contract_file" filename="contract_filename" widget="binary"/>
                                    <field name="contract_filename" invisible="1"/>
                                    <field name="id_card_file" filename="id_card_filename" widget="binary"/>
                                    <field name="id_card_filename" invisible="1"/>
                                </group>
                            </group>
                            <group string="Research Portfolio &amp; Publications">
                                <field name="research_interests" placeholder="e.g. Brand Architecture, Strategic Brand Equity, Global Marketing Management..."/>
                                <field name="publications_summary" placeholder="e.g. Published Books, Key Journal Publications, Citations, Research Grants..."/>
                            </group>
                            <group string="Additional Certified Documents">
                                <field name="attachment_ids" widget="many2many_binary"/>
                            </group>
                            <group string="Administrative Remarks">
                                <field name="notes" nolabel="1" placeholder="Add administrative notes, qualifications, or internal remarks..."/>
                            </group>
                        </page>"""

if target in content:
    content = content.replace(target, replacement, 1)
    with open(views_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("teacher_views.xml updated successfully!")
else:
    print("Target not found in teacher_views.xml.")
