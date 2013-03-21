.. _mail_alias:

mail.alias
============

Models
+++++++

``mail.alias`` is a class for mapping of an email address with a given OpenERP Document model. It is used by OpenERP's mail gateway when processing incoming emails sent to the system. If the recipient address (To) of the message matches a Mail Alias, the message will be either processed following the rules of that alias. If the message is a reply it will be attached to the existing discussion on the corresponding record, otherwise a new record of the corresponding model will be created.
This is meant to be used in combination with a catch-all email configuration on the company's mail server, so that as soon as a new mail.alias is created, it becomes immediately usable and OpenERP will accept email for it.

.. versionchanged:: 7.1

Some Fields
+++++++++++

 - ``alias_name`` : 
      The name of the email alias, e.g. 'jobs'
 - ``alias_model_id`` : 
      The model (OpenERP Document Kind) to which this alias corresponds. Any incoming email that does not reply to an existing record will cause the creation of a new record of this model (e.g. a Project Task)
 - ``alias_defaults`` : 
      A Python dictionary that will be evaluated to provide default values when creating new records for this alias.
 - ``alias_domain`` : 

Methods
+++++++

 - ``name_get`` :
      Return the mail alias display alias_name, inclusing the implicit mail catchall domain from config.
      e.g. `jobs@openerp.my.openerp.com` or `sales@openerp.my.openerp.com`
 - ``create_unique_alias`` :
      Creates an email.alias record according to the values provided in ``vals``, with 2 alterations: the ``alias_name`` value may be suffixed in order to make it unique, and the ``alias_model_id`` value will set to the model ID of the ``model_name`` value, if provided, 
 - ``get_alias`` :
      Return the mail alias for a document (or the default mail alias of the model).
      Arguments:
         model (model OpenERP)
         alias_defaults (A Python dictionary to provide default values when creating new records for this alias.)