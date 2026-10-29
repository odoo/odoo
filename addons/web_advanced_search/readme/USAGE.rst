To use this module, you need to:

* Open *Filters* in a search view
* Select any relational field
* Select operator `is equal to` or `is not equal to`
* The text field changes to a relational selection field where you
  can search for the record in question
* Click *Apply*

To search for properties of linked records (ie invoices for customers
with a credit limit higher than X):

* Open *Filters* in a search view
* Select *Add Advanced Filter*
* Edit the advanced filter
* Click *Save*

Note that you can stack searching for properties: Simply add another
advanced search in the selection search window. You can do
this indefinetely, so it is possible to search for moves belonging
to a journal which has a user who is member of a certain group etc.

Note also the domain dialog offers an editable preview in debug mode:
  .. image:: ../static/img/debug_mode.png
