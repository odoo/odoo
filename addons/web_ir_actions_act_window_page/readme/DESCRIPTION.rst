This addon allows a developer to return the following action types::

{'type': 'ir.actions.act_window.page.next'}

or::

{'type': 'ir.actions.act_window.page.prev'}

which trigger the form's controller to page into the requested direction on the client
side.

A use case could be the case of a validation flow. As a developer, you set up a tree
view with a domain on records to be validated. The user opens the first record in a form
view and validates the record. The validation method returns the 'next' action type so
that the browser window of the user is presented with the next record in the form view.
