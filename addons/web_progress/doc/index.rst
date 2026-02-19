
Adding progress tracking to your code
-------------------------------------

Prerequisites
=============
Progress reporting uses longpolling to send progress data from backend to web client, so make sure that the longpolling is operational before testing this module.


Simple case
===========

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

Advanced case
=============

This module adds methods `web_progress_iter` and `with_progress` to every Odoo model. The only difference between these methods is that `web_progress_iter` requires as its first parameter a collection to iterate upon and `with_progress` iterates always on `self`.

Both methods accept the following optional parameters:

- `msg` (str): an operation description, the message to be shown in the progress report,
- `total` (int): if provided, will be used as a length of the given collection, so `len(collection)` will never be called, which is essential when tracking progress of generators (default is `None`, i.e. `len` will be called),
- `cancellable` (bool): whether cancelling the operation should be possible, i.e visible button "Cancel" (default is `True`),
- `log_level` (str): which log level shall be used when logging progress (default is `"info"`).


.. code-block::

    def action_operation(self, data, length):
        for row in self.web_progress_iter(data, total=length, msg="Message",
                                          cancellable=True, log_level="debug"):
            self.do_something(row)

Another approach
================

You can also add iteration progress reporting to any recordset by adding `progress_iter=True` to its context.

FAQ
---

In this section you will find answers to the common questions concerning progress reporting implemented in `web_progress` module.

How to report a problem or ask a question?
==========================================

Please use the issue tracker of our GitHub repository to report problems or ask questions. You will find it here_.

.. _here: https://github.com/gmarczynski/odoo-web-progress/issues

How the progress reporting works?
=================================
...


How each operation is identified?
=================================

1. Web client injects a unique `progress_code` (UUID) into the context of every RPC call towards backend.

2. Both  `web_progress_iter` and `with_progress` convert the given collection (or generator) into an instance of a generator-like class that uses a `progress_code` from context to perform progress tracking while your code iterates upon the collection.

3. Sheduled (cron) actions have their `progress_code` injected into the context by scheduler prior to their execution.

How often the progress is reported?
===================================

For each `progress_code` (i.e. a unique operation) the first interation (the first element) of the collection wrapped with `web_progress_iter` or `with_progress`  is reported to the web client (via longpolling).

After that, the progress is reported in intervals of minimum **5 seconds** (i.e. any access to any wrapped collection more than 5 seconds after the last reported progress is reported).

Also the final iteration (the last element) of the main wrapped collection (on the top-level) is reported.

What is the overhead of progress reporting?
===========================================
...

How the operation cancelling works?
===================================
...

How multi-level progress reporting works?
=========================================
...

Is the current transaction commited to make progress visible?
=============================================================

No. Progress reporting uses a fresh transaction for each progress report and cancelled operation verification; therefore, the main transation stays untouched and in total isolation.

However, it should be noted that since progress report records and longpolling messages are commited into the database, even if the main transaction is still not commited, the main transaction shall never inspect or change those records in order to avoid inter-transactional conflicts (update-in-parallel exceptions).

Is it possible to put an ongoing operation into background?
===========================================================

Yes, by pressing F5. Actually this is a standard Odoo behaviour that any long-term operation may be put into background by pressing F5. The difference here is that, thanks to system tray menu, user has possibility to follow the progress of ongoing background operations and to cancel them.

Beware that putting an operation to the background makes it impossible to interact further with the user after the operation is finished. So this is OK for data imports (unless there are import errors) and this is definitely not OK for data exports (or reports) that let the user download a generated file after the export operation is finished.


Does progress reporting work with reports?
===========================================

Yes, you can iterate over the wrapped collections in QWeb reports and the progress will be visible to the user.

