##############################################################################
#
# Copyright (c) 2004 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
""" Base event system implementation

"""

#: Applications may register for notification of events by appending a
#: callable to the ``subscribers`` list.
#:
#: Each subscriber takes a single argument, which is the event object
#: being published.
#:
#: Exceptions raised by subscribers will be propagated *without* running
#: any remaining subscribers.
subscribers = []


def notify(event):
    """ Notify all subscribers of ``event``.
    """
    for subscriber in subscribers:
        subscriber(event)
