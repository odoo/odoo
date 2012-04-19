Font style Feature
=====================


This revision adds font style feature in List view.

Font style feature can be used by List view able to define the style of fonts based on the state of records.
we can set the style of fonts bold , italic and underline by defining in the view.

Rng modification
+++++++++++++++++

This revision adds attribute fonts in view.rng

Addon implementation example
++++++++++++++++++++++++++++

In your ``foo`` module, you want to specify that when it is in state ``pending`` then fons of the record should bold in list view

::

<tree string="XYZ"  fonts="bold:state=='pending'">
