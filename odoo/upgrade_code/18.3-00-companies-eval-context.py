import re


def upgrade(file_manager):
    files = [file for file in file_manager if file.path.suffix in ('.xml', '.js', '.py')]
    if not files:
        return

    # Python
    reg_pyfield_domain_allowed_dq = re.compile(r"""(fields\.([^\)]+?\s*)domain="([^"]+)?\s*)allowed_company_ids(\s*([^"]+)?")""")
    reg_pyfield_domain_allowed_sq = re.compile(r"""(fields\.([^\)]+?\s*)domain='([^']+)?\s*)allowed_company_ids(\s*([^']+)?')""")
    reg_pyfield_domain_current_dq = re.compile(r"""(fields\.([^\)]+?\s*)domain="([^"]+)?\s*)current_company_id(\s*([^"]+)?")""")
    reg_pyfield_domain_current_sq = re.compile(r"""(fields\.([^\)]+?\s*)domain='([^']+)?\s*)current_company_id(\s*([^']+)?')""")

    # XML
    reg_action_domain_allowed = re.compile(r"""(<field[^>]* name=["']domain["'][^>]*>([^<>]+)?\s*)allowed_company_ids(\s*([^<>]+)?</field>)""")
    reg_action_domain_current = re.compile(r"""(<field[^>]* name=["']domain["'][^>]*>([^<>]+)?\s*)current_company_id(\s*([^<>]+)?</field>)""")
    reg_action_context_allowed = re.compile(r"""(<field[^>]* name=["']context["'][^>]*>([^<>]+)?\s*)allowed_company_ids(\s*([^<>]+)?</field>)""")
    reg_action_context_current = re.compile(r"""(<field[^>]* name=["']context["'][^>]*>([^<>]+)?\s*)current_company_id(\s*([^<>]+)?</field>)""")
    reg_attribute_domain_allowed = re.compile(r"""(<attribute name="domain">*([^<>]+)?\s*)allowed_company_ids(\s*([^<>]+)?</attribute>)""")
    reg_attribute_domain_current = re.compile(r"""(<attribute name="domain">*([^<>]+)?\s*)current_company_id(\s*([^<>]+)?</attribute>)""")
    reg_field_domain_allowed = re.compile(r"""(<field([^>]+?\s*)domain=['"]\[([^<>]+)? \s*)allowed_company_ids(\s*([^<>]+)?\]['"])""")
    reg_field_domain_current = re.compile(r"""(<field([^>]+?\s*)domain=['"]\[([^<>]+)? \s*)current_company_id(\s*([^<>]+)?\]['"])""")
    reg_attr_allowed = re.compile(r"""(<(button|group|label|div|field|separator|footer|page|widget|xpath)([^>]+?\s*)(readonly|required|invisible|column_invisible)="([^<>"]+)?\s*)(?<!context.get\(.)allowed_company_ids(\s*([^<>]+)?")""")
    reg_attr_current = re.compile(r"""(<(button|group|label|div|field|separator|footer|page|widget|xpath)([^>]+?\s*)(readonly|required|invisible|column_invisible)="([^<>"]+)?\s*)current_company_id(\s*([^<>]+)?")""")

    # companies.active_ids[0] -> companies.active_id
    reg_active_ids_0 = re.compile(r'companies\.active_ids\[0\]')

    for fileno, file in enumerate(files, start=1):
        content = file.content
        content = reg_pyfield_domain_allowed_dq.sub(r'\1companies.active_ids\4', content)
        content = reg_pyfield_domain_allowed_sq.sub(r'\1companies.active_ids\4', content)
        content = reg_pyfield_domain_current_dq.sub(r'\1companies.active_id\4', content)
        content = reg_pyfield_domain_current_sq.sub(r'\1companies.active_id\4', content)

        content = reg_action_domain_allowed.sub(r'\1companies.active_ids\3', content)
        content = reg_action_domain_current.sub(r'\1companies.active_id\3', content)
        content = reg_action_context_allowed.sub(r'\1companies.active_ids\3', content)
        content = reg_action_context_current.sub(r'\1companies.active_id\3', content)
        content = reg_attribute_domain_allowed.sub(r'\1companies.active_ids\3', content)
        content = reg_attribute_domain_current.sub(r'\1companies.active_id\3', content)
        content = reg_field_domain_allowed.sub(r'\1companies.active_ids\4', content)
        content = reg_field_domain_current.sub(r'\1companies.active_id\4', content)
        content = reg_attr_allowed.sub(r'\1companies.active_ids\6', content)
        content = reg_attr_current.sub(r'\1companies.active_id\6', content)

        content = reg_active_ids_0.sub('companies.active_id', content)
        file.content = content

        file_manager.print_progress(fileno, len(files))
