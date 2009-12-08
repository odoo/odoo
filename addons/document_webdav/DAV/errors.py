#!/usr/bin/env python
"""

    Exceptions for the DAVserver implementation

"""

class DAV_Error(Exception):
    """ in general we can have the following arguments:

	1. the error code
	2. the error result element, e.g. a <multistatus> element
    """

    def __init__(self,*args):
        if len(args)==1:
            self.args=(args[0],"")
        else:
            self.args=args
    
class DAV_Secret(DAV_Error):
    """ the user is not allowed to know anything about it
    
    returning this for a property value means to exclude it
    from the response xml element.
    """

    def __init__(self):
        DAV_Error.__init__(self,0)
        pass

class DAV_NotFound(DAV_Error):
    """ a requested property was not found for a resource """
    
    def __init__(self,*args):
        if len(args):
	    if isinstance(args[0],list):
		stre = "Path %s not found!"%('/'.join(args[0]))
	    else:
	        stre = args[0]
            DAV_Error.__init__(self,404,stre)
        else:
            DAV_Error.__init__(self,404)

        pass

class DAV_Forbidden(DAV_Error):
    """ a method on a resource is not allowed """
    
    def __init__(self,*args):
        if len(args):
            DAV_Error.__init__(self,403,args[0])
        else:
            DAV_Error.__init__(self,403)
        pass

