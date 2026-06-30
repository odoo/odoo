def upgrade(file_manager):
    files = [
        f for f in file_manager
        if 'controllers' in f.path.parts
        if f.path.suffix == '.py'
    ]

    for fileno, file in enumerate(files):
        file.content = file.content.replace(
            'type="json",', 'type="jsonrpc",'
        ).replace(
            "type='json',", "type='jsonrpc',"
        )
        file_manager.print_progress(fileno, len(files))
