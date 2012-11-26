.. _on_change_tips:

On Change Methods
=================

Definition of on change methods in a view looks like this:

::

    <field name="name" on_change="name_change(name, address, city)"/>

And here is the corresponding method in the model:

::

    def name_change(self, cr, uid, ids, name, address, city, context=None):
        ...
        return {
            'value': {
                'address': ...
                'city': ...
            }
        }

On change methods can be confusing when people use them, here are a list of clarifications to avoid any misconception:

- On change methods can be executed during the creation of a row, long before it is effectively saved into the database.
- Fields are *not* validated before going through a on change methods. As an example, a field marqued as required can be False.
- On change methods can read data in the database but should *never* attempt to write anything, this is always a strong conception
  problem.
- The format of the values passed to an on change method is exactly the same than the one passed to the write() method. So
  the on change method must be able to handle any format used for all the fields it process. The following list describe some fields
  that can have an unusual format.

  - *float*: Due to the way JSON represents numbers and the way the JSON library of Python handles it, a float field will not always
    be represented as a python float type. When the number can be represented as an integer it will appear as a python integer type.
    This can be a problem when using some mathematical operations (example: price / 2), so it is a good practice to always cast any number
    to float when you want to handle floats in on change methods.
  - *one2many and many2many*: There are plenty of misconception about x2many fields in on change methods. The reality is, in fact, quite
    complex. x2many are defined by a list of operations, each operation was given a number (0 -> create, 1 -> write, ect...) and has
    its own semantic. To be able to use one2many and many2many in on change methods, you are strongly encourage to use the
    resolve_2many_commands() method. Here is a sample usage:

    ::

        values = self.resolve_2many_commands(cr, uid, 'my_o2m', my_o2m_values, ['price', 'tax'], context)

    This code will convert the complex list of operations that makes the o2m value into a simple list of dictionaries containing the fields
    'price' and 'tax', which is way simpler to handle in most on change methods. Please note that you can also return a list of
    dictionaries as the new value of a one2many, it will replace the actual rows contained in that one2many (but it will also remove the
    previous ones).