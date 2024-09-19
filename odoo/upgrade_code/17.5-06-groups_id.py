import re


def upgrade(file_manager):
    nb = len([1 for file in file_manager if file.path.name.rsplit('.', 1)[1] in ('xml', 'js', 'py')])
    i = 0
    file_manager.print_progress(0, nb)

    reg_groups_id_in = re.compile(r'\bgroups_id\b(.*\bin\b)')
    reg_in_groups_id = re.compile(r'(\bin\b.*)\bgroups_id\b')
    reg_groups_id = re.compile(r'\bgroups_id\b')

    for file in file_manager:
        if file.path.name.rsplit('.', 1)[1] in ('xml', 'js', 'py'):
            content = file.content
            content = reg_groups_id_in.sub(r'group_ids.all_implied_ids\1', content)
            content = reg_in_groups_id.sub(r'\1group_ids.all_implied_ids', content)
            content = reg_groups_id.sub(r'group_ids', content)
            file.content = content

            i += 1
            file_manager.print_progress(i, nb)
