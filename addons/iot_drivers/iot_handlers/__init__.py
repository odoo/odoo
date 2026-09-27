import logging
import importlib
from pathlib import Path
from itertools import chain
from ..tools.system import IS_WINDOWS, IS_TEST

_logger = logging.getLogger(__name__)

# Only import files that correspond to the current platform (Linux or Windows)
exclude_suffix = '_L' if IS_WINDOWS else '_W'

drivers_path = Path(__file__).parent / 'drivers'
interfaces_path = Path(__file__).parent / 'interfaces'

for file_path in chain(drivers_path.glob('*.py'), interfaces_path.glob('*.py')):
    module = file_path.stem
    if IS_TEST or any(module.endswith(suffix) for suffix in ['__', exclude_suffix]):
        continue

    try:
        importlib.import_module(f'.{file_path.parent.name}.{module}', package=__package__)
    except Exception:  # noqa: BLE001
        _logger.exception("Could not load module %s", module)
