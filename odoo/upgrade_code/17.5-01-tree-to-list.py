import re


def upgrade(file_manager):
    files = [file for file in file_manager if file.path.suffix in ('.xml', '.js', '.py')]
    if not files:
        return

    reg_tree_to_list_xml_mode = re.compile(r"""(<field[^>]* name=["'](view_mode|name|binding_view_types)["'][^>]*>([^<>]+,)?\s*)tree(\s*(,[^<>]+)?</field>)""")
    reg_tree_to_list_tag = re.compile(r'\n([^:\n]|:(?!//))+([<,/])tree([ \n\r,>/])')
    reg_tree_to_list_xpath = re.compile(r"""(<xpath[^>]* expr=['"])([^<>]*/)?tree(/|[\['"])""")
    reg_tree_to_list_ref = re.compile(r'tree_view_ref')
    reg_tree_to_list_mode = re.compile(r"""(mode=['"][^'"]*)tree([^'"]*['"])""")
    reg_tree_to_list_view_mode = re.compile(r"""(['"]view_mode['"][^'":=]*[:=].*['"]([^'"]+,)?\s*)tree(\s*(,[^'"]+)?['"])""")
    reg_tree_to_list_view = re.compile(r"""(['"]views['"][^'":]*[:=].*['"])tree(['"])""")
    reg_tree_to_list_string = re.compile(r"""([ '">)])tree( [vV]iews?[ '"<.)])""")
    reg_tree_to_list_String = re.compile(r"""([ '">)])Tree( [vV]iews?[ '"<.)])""")
    reg_tree_to_list_env_ref = re.compile(r"""(self\.env\.ref\(.*['"])tree(['"])""")

    for fileno, file in enumerate(files, start=1):
        content = file.content
        content = content.replace(' tree view ', ' list view ')
        content = reg_tree_to_list_xml_mode.sub(r'\1list\4', content)
        content = reg_tree_to_list_tag.sub(r'\1list\2', content)
        content = reg_tree_to_list_xpath.sub(r'\1\2list\3', content)
        content = reg_tree_to_list_ref.sub('list_view_ref', content)
        content = reg_tree_to_list_mode.sub(r'\1list\2', content)
        content = reg_tree_to_list_view_mode.sub(r'\1list\3', content)
        content = reg_tree_to_list_view.sub(r'\1list\2', content)
        content = reg_tree_to_list_string.sub(r'\1list\2', content)
        content = reg_tree_to_list_String.sub(r'\1List\2', content)
        content = reg_tree_to_list_env_ref.sub(r'\1list\2', content)
        file.content = content

        file_manager.print_progress(fileno, len(files))
