import bs4
import warnings


def patch_module():
    # ofxparse use an html parser to parse ofx xml files and triggers a warning since bs4 4.11.0
    # https://github.com/jseutter/ofxparse/issues/170
    warnings.filterwarnings('ignore', category=bs4.XMLParsedAsHTMLWarning)
