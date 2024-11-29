import mimetypes


def patch_mimetypes():
    # if extension is already knows, the new definition will remplace the existing one
    # Add potentially missing (older ubuntu) font mime types
    mimetypes.add_type('application/font-woff', '.woff')
    mimetypes.add_type('application/vnd.ms-fontobject', '.eot')
    mimetypes.add_type('application/x-font-ttf', '.ttf')
    mimetypes.add_type('image/webp', '.webp')
    # Add potentially wrong (detected on windows) svg mime types
    mimetypes.add_type('image/svg+xml', '.svg')
    # this one can be present on windows with the value 'text/plain' which
    # breaks loading js files from an addon's static folder
    mimetypes.add_type('text/javascript', '.js')
