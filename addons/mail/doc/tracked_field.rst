Tracked fields
---------------
Tracked fields is generic logging system for the changes applied to some fields in open chatter.
 - In the definition of a fields. you have to simply add tracked=True.
 - When changing one of the fields having tracked=True on saved automatically write a log in openchatter for the changes in fields.

How it works:
+++++++++++++
 - You have to add tracked=True in field defination as following.
 - ``'stage_id': fields.many2one('project.task.type', 'Stage',tracked=True),``
 - For developed this feature we override write method of mail_thread. 
 - And make one mako template which shows old field and updated field.
 
Open chatter log:
+++++++++++++++++
 - After changing field follower can show log of tracked field in open chatter as followed.
     - Updated Fields:
           - Stage: Analysis -> Specification