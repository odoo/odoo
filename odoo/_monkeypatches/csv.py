import csv


def patch_module():
    """ The default limit for CSV fields in the module is 128KiB,
    which is not quite sufficient to import images to store
    in attachment. 500MiB is a bit overkill, but better safe
    than sorry I guess
    """
    class UNIX_LINE_TERMINATOR(csv.excel):
        lineterminator = '\n'
    csv.field_size_limit(500 * 1024 * 1024)
    csv.register_dialect("UNIX", UNIX_LINE_TERMINATOR)
