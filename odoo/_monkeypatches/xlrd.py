def patch_module():
    try:
        from xlrd import xlsx  # noqa: PLC0415
    except ImportError:
        xlsx = None
    else:
        from lxml import etree  # noqa: PLC0415
        # xlrd.xlsx supports defusedxml, defusedxml's etree interface is broken
        # (missing ElementTree and thus ElementTree.iter) which causes a fallback to
        # Element.getiterator(), triggering a warning before 3.9 and an error from 3.9.
        #
        # Historically we had defusedxml installed because zeep had a hard dep on
        # it. They have dropped it as of 4.1.0 which we now require (since 18.0),
        # but keep this patch for now as Odoo might get updated in a legacy env
        # which still has defused.
        #
        # Directly instruct xlsx to use lxml as we have a hard dependency on that.
        xlsx.ET = etree
        xlsx.ET_has_iterparse = True
        xlsx.Element_has_iter = True
