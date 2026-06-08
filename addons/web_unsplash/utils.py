UNSPLASH_ACCESS_KEY_ICP = 'unsplash.access_key'
UNSPLASH_APP_ID_ICP = 'unsplash.app_id'


def get_unsplash_access_key(IrConfigParameter):
    """
    Return the access key for Unsplash.
    Note: This method serves as a hook for modules that would override it.
    """
    return IrConfigParameter.sudo().get_str(UNSPLASH_ACCESS_KEY_ICP)


def get_unsplash_app_id(IrConfigParameter):
    """
    Return the app ID for Unsplash.
    Note: This method serves as a hook for modules that would override it.
    """
    return IrConfigParameter.sudo().get_str(UNSPLASH_APP_ID_ICP)
