Mail module documentation
=========================

The Mail module holds all models and logic related to messages management. At low-level, it handles messages and offers an API to message queues for email sending. At an higher level, it provides the OpenChatter feature that is a thread management system inside OpenERP. A model that inherits from the mail module adds OpenChatter to its document. Its gives them the following capabilities :

 - messages management with a threaded design
 - subscription mechanism tha allow users to follow/unfollow documents
 - notifications mechanism; notifications are pushed to users to form a Wall page holding the latest pushed messages

The mail module also comes with an email composition wizard, along with discussion groups.

.. include:: index.rst.inc
