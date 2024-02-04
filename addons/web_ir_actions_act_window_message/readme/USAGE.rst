Depend on this module and return

.. code:: python

    {
        'type': 'ir.actions.act_window.message',
        'title': _('My title'),
        'message': _('My message'),
        # optional title of the close button, if not set, will be _('Close')
        # if set False, no close button will be shown
        # you can create your own close button with an action of type
        # ir.actions.act_window_close
        'close_button_title': 'Make this window go away',
        # Use HTML instead of text
        'is_html_message': True,
        # this is an optional list of buttons to show
        'buttons': [
            # a button can be any action (also ir.actions.report.xml et al)
            {
                'type': 'ir.actions.act_window',
                'name': 'All customers',
                'res_model': 'res.partner',
                'view_mode': 'form',
                'views': [[False, 'list'], [False, 'form']],
                'domain': [('customer', '=', True)],
            },
            # or if type == method, you need to pass a model, a method name and
            # parameters
            {
                'type': 'method',
                'name': _('Yes, do it'),
                'model': self._name,
                'method': 'myfunction',
                # list of arguments to pass positionally
                'args': [self.ids],
                # dictionary of keyword arguments
                'kwargs': {'force': True},
                # button style
                'classes': 'btn-primary',
            }
        ]
    }

You are responsible for translating the messages.
