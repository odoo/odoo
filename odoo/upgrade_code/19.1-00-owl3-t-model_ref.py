import re
import logging

_logger = logging.getLogger(__name__)


def upgrade(file_manager):
    files = [file for file in file_manager if file.path.suffix == '.xml']
    if not files:
        return

    reg_t_model = re.compile(r'(?<!-)t-model(\s*=)')
    reg_t_ref = re.compile(r'(?<!-)t-ref(\s*=)')

    for fileno, file in enumerate(files, start=1):
        try:
            raw_content = file.path.read_bytes()
            content = raw_content.decode("utf-8", errors="ignore")

            initial_content = content

            if 't-model' in content:
                content = reg_t_model.sub(r't-custom-model\1', content)

            if 't-ref' in content:
                content = reg_t_ref.sub(r't-custom-ref\1', content)

            if content != initial_content:
                file.content = content

        except Exception as e:
            _logger.info("Skipping %s due to error: %s", file.path, e)

        file_manager.print_progress(fileno, len(files))
