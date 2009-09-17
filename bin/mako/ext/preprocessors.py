"""preprocessing functions, used with the 'preprocessor' argument on Template, TemplateLookup"""

import re

def convert_comments(text):
    """preprocess old style comments.
    
    example:
    
    from mako.ext.preprocessors import convert_comments
    t = Template(..., preprocessor=preprocess_comments)"""
    return re.sub(r'(?<=\n)\s*#[^#]', "##", text)

# TODO
def create_tag(callable):
    """given a callable, extract the *args and **kwargs, and produce a preprocessor
    that will parse for <%<funcname> <args>> and convert to an appropriate <%call> statement.
    
    this allows any custom tag to be created which looks like a pure Mako-style tag."""
    raise NotImplementedError("Future functionality....")