## Demonstrates a "push" subscription with a callback function
from __future__ import annotations

from time import sleep

import win32evtlog

query_text = '*[System[Provider[@Name="Microsoft-Windows-Winlogon"]]]'


def c(reason, context, evt):
    if reason == win32evtlog.EvtSubscribeActionError:
        print("EvtSubscribeActionError")
    elif reason == win32evtlog.EvtSubscribeActionDeliver:
        print("EvtSubscribeActionDeliver")
    else:
        print("??? Unknown action ???", reason)
    context.append(win32evtlog.EvtRender(evt, win32evtlog.EvtRenderEventXml))
    return 0


evttext: list[str] = []
s = win32evtlog.EvtSubscribe(
    "System",
    win32evtlog.EvtSubscribeStartAtOldestRecord,
    Query="*",
    Callback=c,
    Context=evttext,
)

sleep(0.001)
print("\n".join(evttext))
