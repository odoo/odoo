To use this functionality you need to return following action with list of actions to execute:

.. code-block:: python

      def foo(self):
         self.ensure_one()
         return {
            'type': 'ir.actions.act_multi',
            'actions': [
                {'type': 'ir.actions.act_window_close'},
                {'type': 'ir.actions.client', 'tag': 'reload'},
            ]
         }
