.. _changelog:

Changelog
=========

`trunk (saas-3)`
++++++++++++++++

- created ``website_portal`` menu, build on defunct document_page module.
- added new feature ``Inline Discussion`` , that will allow a user to comment
  on every paragraph on portal post
- added new feature ``Select to Tweet``, that will alllow a user tweet a
  selected text from portal to post , directly on twitter.

WebsitePortal(controller)
=======================

Methods
+++++++

- ``portal`` : remove routing related to date.
- ``portal_post`` : updated with , suggestion of next post to the user based on
  cookie and number of views.
- ``discussion`` : added method , contains a detail of discussion on every
  paragraph, if count is true it only return len of ids else return full
  detail.
- ``post_discussion`` : added methodt, that allow to post discussion on any
  paragraph.
- ``change_bg`` : added method allow a user to change background image on portal
  post from front-end.
- ``get_user`` : added method , that will return True if user is public else False.

