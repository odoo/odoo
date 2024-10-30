import csv


def patch_csv():
    """ The default limit for CSV fields in the module is 128KiB, which is not
        quite sufficient to import images to store in attachment. 500MiB is a
        bit overkill, but better safe than sorry I guess
    """
    csv.field_size_limit(500 * 1024 * 1024)
