""" View validation code (using assertions, not the RNG schema). """

def valid_page_in_book(arch):
    """A `page` node must be below a `book` node."""
    return not arch.xpath('//page[not(ancestor::notebook)]')

def valid_view(arch):
    if arch.tag == 'form':
        for pred in [valid_page_in_book]:
            if not pred(arch):
                return False
    return True
