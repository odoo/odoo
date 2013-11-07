.. _crm_meeting:

Fields:
+++++++
 - ``is_attendee`` :
    function field , that defined whether loged in user is attendee or not.
 - ``attendee_status``:
    function field , that defined login user status, either accepted, declined or needs-action.
 - ``event_time``:
    function field, defined an event_time in user's tz.

Methods:
++++++++
 - ``_find_user_attendee``:
    return attendee if attendee is internal user else false.
 - ``_compute_time``:
    compute a time from date_start and duration with user's tz.
 - ``search``:
    search a current user's meetings
 - ``do_accept/do_decline``:
    trigger when ,user accept/decline from the meeting form view.
 - ``get_attendee``:
    get detail of attendees meeting.
 - ``get_interval``:
    call from email template that return formate of date, as per value pass from the email template.

views:
++++++
 - ``do_accept``:
    Accept button in meeting form view that is allow a user to accept a meeting ,that is visible to only attendee and if attendee state is other than accepted.
 - ``do_decline``:
    Decline button in meeting form view that is allow a user to accept a meeting ,that is visible to only attendee and if attendee state is other than declined.
 - ``chatter(message_ids)``: 
    show a log of meeting.

security:
+++++++++
    - added record rule to restrict an user to show personal invitation on meeting , so user can't change other's status , from invitation tab.
