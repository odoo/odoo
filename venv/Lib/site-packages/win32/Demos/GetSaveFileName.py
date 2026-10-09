import os

import win32con
import win32gui

filter = "Python Scripts\0*.py;*.pyw;*.pys\0Text files\0*.txt\0"
customfilter = "Other file types\0*.*\0"

fname, customfilter, flags = win32gui.GetSaveFileNameW(
    InitialDir=os.environ["temp"],
    Flags=win32con.OFN_ALLOWMULTISELECT | win32con.OFN_EXPLORER,
    File="somefilename",
    DefExt="py",
    Title="GetSaveFileNameW",
    Filter=filter,
    CustomFilter=customfilter,
    FilterIndex=1,
)

print(f"save file names: {fname!r}")
print(f"filter used: {customfilter!r}")
print(f"Flags: {flags}")
for k, v in win32con.__dict__.items():
    if k.startswith("OFN_") and flags & v:
        print("\t" + k)

fname, customfilter, flags = win32gui.GetOpenFileNameW(
    InitialDir=os.environ["temp"],
    Flags=win32con.OFN_ALLOWMULTISELECT | win32con.OFN_EXPLORER,
    File="somefilename",
    DefExt="py",
    Title="GetOpenFileNameW",
    Filter=filter,
    CustomFilter=customfilter,
    FilterIndex=0,
)

print(f"open file names: {fname!r}")
print(f"filter used: {customfilter!r}")
print(f"Flags: {flags}")
for k, v in win32con.__dict__.items():
    if k.startswith("OFN_") and flags & v:
        print("\t" + k)
