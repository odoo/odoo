from . import test_avatax

# Tests for the certification badges
# https://developer.avalara.com/certification/avatax/
from . import (
    test_address_validation,
    # test_communication        # badge not supported (yet?)
    # test_document_management  # badge not supported (yet?)
    # test_extractor            # badge not supported (yet?)
    test_refunds,
    # test_tax_content          # badge not supported (yet?)
    test_use_tax,
    test_vat,
    test_avatax_unique_code,
)
