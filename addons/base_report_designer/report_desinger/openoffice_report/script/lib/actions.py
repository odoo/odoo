import uno
import unohelper
import os
#--------------------------------------------------
# An ActionListener adapter.
# This object implements com.sun.star.awt.XActionListener.
# When actionPerformed is called, this will call an arbitrary
#  python procedure, passing it...
#   1. the oActionEvent
#   2. any other parameters you specified to this object's constructor (as a tuple).
if __name__<>"package":
    os.system( "ooffice '-accept=socket,host=localhost,port=2002;urp;'" )
passwd=""
database=""
uid=""
loginstatus=False
from com.sun.star.awt import XActionListener
class ActionListenerProcAdapter( unohelper.Base, XActionListener ):
    def __init__( self, oProcToCall, tParams=() ):
        self.oProcToCall = oProcToCall # a python procedure
        self.tParams = tParams # a tuple

    # oActionEvent is a com.sun.star.awt.ActionEvent struct.
    def actionPerformed( self, oActionEvent ):
        if callable( self.oProcToCall ):
            apply( self.oProcToCall, (oActionEvent,) + self.tParams )

#--------------------------------------------------
# An ItemListener adapter.
# This object implements com.sun.star.awt.XItemListener.
# When itemStateChanged is called, this will call an arbitrary
#  python procedure, passing it...
#   1. the oItemEvent
#   2. any other parameters you specified to this object's constructor (as a tuple).
from com.sun.star.awt import XItemListener
class ItemListenerProcAdapter( unohelper.Base, XItemListener ):
    def __init__( self, oProcToCall, tParams=() ):
        self.oProcToCall = oProcToCall # a python procedure
        self.tParams = tParams # a tuple

    # oItemEvent is a com.sun.star.awt.ItemEvent struct.
    def itemStateChanged( self, oItemEvent ):
        if callable( self.oProcToCall ):
            apply( self.oProcToCall, (oItemEvent,) + self.tParams )

#--------------------------------------------------
# An TextListener adapter.
# This object implements com.sun.star.awt.XTextistener.
# When textChanged is called, this will call an arbitrary
#  python procedure, passing it...
#   1. the oTextEvent
#   2. any other parameters you specified to this object's constructor (as a tuple).
from com.sun.star.awt import XTextListener
class TextListenerProcAdapter( unohelper.Base, XTextListener ):
    def __init__( self, oProcToCall, tParams=() ):
        self.oProcToCall = oProcToCall # a python procedure
        self.tParams = tParams # a tuple

    # oTextEvent is a com.sun.star.awt.TextEvent struct.
    def textChanged( self, oTextEvent ):
        if callable( self.oProcToCall ):
            apply( self.oProcToCall, (oTextEvent,) + self.tParams )


