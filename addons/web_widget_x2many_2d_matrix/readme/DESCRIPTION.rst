This module allows to show an x2many field with 3-tuples
($x_value, $y_value, $value) in a table

+-----------+-------------+-------------+
|           | $x_value1   | $x_value2   |
+===========+=============+=============+
| $y_value1 | $value(1/1) | $value(2/1) |
+-----------+-------------+-------------+
| $y_value2 | $value(1/2) | $value(2/2) |
+-----------+-------------+-------------+

where `value(n/n)` is editable.

An example use case would be: Select some projects and some employees so that
a manager can easily fill in the planned_hours for one task per employee. The
result could look like this:

.. image:: https://raw.githubusercontent.com/OCA/web/12.0/web_widget_x2many_2d_matrix/static/description/screenshot.png
    :alt: Screenshot

The beauty of this is that you have an arbitrary amount of columns with this
widget, trying to get this in standard x2many lists involves some quite ugly
hacks.
