|Travis|_ |Coveralls|_ |Docs|_ |PyPI|_

.. |Travis| image:: https://api.travis-ci.org/python-excel/xlwt.svg?branch=master
.. _Travis: https://travis-ci.org/python-excel/xlwt

.. |Coveralls| image:: https://coveralls.io/repos/python-excel/xlwt/badge.svg?branch=master
.. _Coveralls: https://coveralls.io/r/python-excel/xlwt?branch=master

.. |Docs| image:: https://readthedocs.org/projects/xlwt/badge/?version=latest
.. _Docs: https://xlwt.readthedocs.org/en/latest/

.. |PyPI| image:: https://badge.fury.io/py/xlwt.svg
.. _PyPI: https://badge.fury.io/py/xlwt

xlwt
====

This is a library for developers to use to generate
spreadsheet files compatible with Microsoft Excel versions 95 to 2003.

The package itself is pure Python with no dependencies on modules or packages
outside the standard Python distribution.

Please read this before using this package:
https://groups.google.com/d/msg/python-excel/P6TjJgFVjMI/g8d0eWxTBQAJ

Installation
============

Do the following in your virtualenv::

  pip install xlwt

Quick start
===========

.. code-block:: python

    import xlwt
    from datetime import datetime

    style0 = xlwt.easyxf('font: name Times New Roman, color-index red, bold on',
        num_format_str='#,##0.00')
    style1 = xlwt.easyxf(num_format_str='D-MMM-YY')

    wb = xlwt.Workbook()
    ws = wb.add_sheet('A Test Sheet')

    ws.write(0, 0, 1234.56, style0)
    ws.write(1, 0, datetime.now(), style1)
    ws.write(2, 0, 1)
    ws.write(2, 1, 1)
    ws.write(2, 2, xlwt.Formula("A3+B3"))

    wb.save('example.xls')


Documentation
=============

Documentation can be found in the ``docs`` directory of the xlwt package.
If these aren't sufficient, please consult the code in the
examples directory and the source code itself.

The latest documentation can also be found at:
https://xlwt.readthedocs.org/en/latest/

Problems?
=========
Try the following in this order:

- Read the source

- Ask a question on https://groups.google.com/group/python-excel/

Acknowledgements
================

xlwt is a fork of the pyExcelerator package, which was developed by
Roman V. Kiseliov. This product includes software developed by
Roman V. Kiseliov <roman@kiseliov.ru>.

xlwt uses ANTLR v 2.7.7 to generate its formula compiler.


