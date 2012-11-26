Font style in list views
========================

.. versionadded:: 7.0

This revision adds font styles in list views. Before this revision it was
possible to define some colors in list view. This revision allows to define 
the a font style, based on an evaluated Python expression. The definition syntax is 
the same than the colors feature. Supported styles are bold, italic and 
underline.

Rng modification
+++++++++++++++++

This revision adds the ``fonts`` optional attribute in ``view.rng``.

Addon implementation example
++++++++++++++++++++++++++++

In your ``foo`` module, you want to specify that when any record is in ``pending`` 
state then it should be displayed in bold in the list view. Edit your foo_view.xml
file that define the views, and add the fonts attribute to the tree tag.

.. code-block:: xml

  <tree string="Foo List View" fonts="bold:state=='pending'">
    [...]
  </tree>
