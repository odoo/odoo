====================
Dynamic Progress Bar
====================

Progress bar for Odoo waiting screen, possibility to cancel an ongoing operation and a sys tray menu for all operations in progress.

.. class:: no-web

    .. image:: https://raw.githubusercontent.com/gmarczynski/odoo-web-progress/14.0/web_progress/static/description/progress_bar_loading_cancelling.gif
        :alt: Progress Bar
        :width: 100%
        :align: center


**web_progress** exists for Odoo 11.0, 12.0, 13.0, 14.0, 15.0, 16.0 (CE and EE).

Author: Grzegorz Marczyński

License: LGPL-3.

Copyright © 2023 Grzegorz Marczyński


Features
--------

.. class:: no-web

    .. image:: https://raw.githubusercontent.com/gmarczynski/odoo-web-progress/14.0/web_progress/static/description/progress_bar_loading_systray.gif
        :alt: Progress Systray Menu
        :width: 50%
        :align: right

- progress reporting for all standard Odoo import and export operations
- system tray menu that lists ongoing operations initiated by the logged user (all operations visible to Administrator)
- support for all operations initiated through UI and executed by planned activities (cron)
- generator-like method to simply add progress reporting to any iteration (support for sub-iterations)


For developers
---------------

Typically when your code executes any long-term operation there is a loop over a `collection` in your code.

In order to report progress of the operation, wrap the `collection` with `self.web_progress_iter(collection, msg="Message")`

Say, your operation's main method looks as follows:

.. code-block::

    def action_operation(self):
        for rec in self:
            rec.do_somethig()


Then a progress-reporting-ready version would be:

.. code-block::

    def action_operation(self):
        for rec in self.web_progress_iter(self, msg="Message"):
            rec.do_something()


or a simpler version for recordsets:

.. code-block::

    def action_operation(self):
        for rec in self.with_progress(msg="Message"):
            rec.do_something()

Progress tracking may be added to sub-operations as well:

.. code-block::

    def action_operation(self):
        for rec in self.with_progress(msg="Message"):
            lines = rec.get_lines()
            for line in lines.with_progress("Sub-operation")
                line.do_something()

Release Notes
-------------

2.0 - 2023-01-29
- port to Odoo 16.0

2.0 - 2021-08-22 - new functionality and fixes:

- add styles (standard, simple, nyan cat)
- make the progress bar appear directly when the screen becomes blocked
- keep basic progress functionality even if long polling is disabled or cease to work
- fix import of o2m fields for Odoo v13.0 and v0.14

1.4 - 2021-03-21 - fixes:

- fix deadlock on bus.bus garbage collection
- fix deadlock on access to res.users
- do not animate but set the progress bar going backwards


1.3 - 2019-07-15 - new functionality

- estimated time left / total


1.2 - 2019-06-24 - fixes:

- refactor global progress data
- change progress template name to avoid clash with progressbar widget

1.1 - 2019-06-23 - fixes:

- remove unecessary dependency on multiprocessing
- fix memory leak in time-tracking internal data

1.0 - 2019-06-20 - initial version
