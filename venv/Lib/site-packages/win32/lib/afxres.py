import warnings

from pywin.mfc.afxres import *

warnings.warn(
    "Importing the global `afxres` module is deprecated. Import from `pywin.mfc.afxres` instead.",
    category=DeprecationWarning,
)
