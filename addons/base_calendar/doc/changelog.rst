.. _changelog:

Changelog
=========

Email Template of Meeting Invitation:
+++++++++++++++++++++++++++++++++++++
 - remove static code of HTML design of email of meeting invitation
 - added new better layout of email of meeting invitation using MAKO Template.

Web controller:
+++++++++++++++
 - ``accept`` :
    handle request ('meeting_invitation/accept') ,when accepted an invitation it change the status of invitation as accepted , user do need to login in system.
 - ``declined``:
    handle request ('meeting_invitation/decline') ,when declined an invitation it change the status of invitation as declined , user do need to login in system.
 - ``view``:
    handle request ('meeting_invitation/view') ,when user click on accept,declined link button , it redirect user to form view if user is already login and if user has not been login it redirect to a simple qweb template to inform user has accepted/declined a meeting ,if user click on directly in openerp it redirect user to a meeting calendar view , if user is not login then it redirect to a qweb template.
 - ``check_security``:
    check token is valid and user is not allow to accept/decline invitation mail of other user from email template URL.

Web Widget:
+++++++++++
 - ``Field Many2Many_invite``(widget):
    display a status button in left side of every invited attendees of meeting , in many2many.

Qweb Template:
++++++++++++++
 - added template ,to directly allow any invited user to accept , decline a meeting , if user do not need to login in the system to accept or decline  an invitation.
