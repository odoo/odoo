This new field type can be used in the same way as the odoo 'Image'
field type.

``` python
from odoo import models
from odoo.addons.fs_image.fields import FSImage

class MyModel(models.Model):
    _name = 'my.model'

    image = FSImage('Image', max_width=1920, max_height=1920)
```

``` xml
<record id="my_model_form" model="ir.ui.view">
    <field name="name">my.model.form</field>
    <field name="model">my.model</field>
    <field name="arch" type="xml">
        <form>
            <sheet>
                <group>
                    <field name="image" class="oe_avatar"/>
                </group>
            </sheet>
        </form>
    </field>
</record>
```

In the example above, the image will be resized to 1920x1920px if it is
larger than that. The widget used in the form view will also allow the
user set an 'alt' text for the image.

A mode advanced and useful example is the following:

``` python
from odoo import models
from odoo.addons.fs_image.fields import FSImage

class MyModel(models.Model):
    _name = 'my.model'

    image_1920 = FSImage('Image', max_width=1920, max_height=1920)
    image_128 = FSImage('Image', max_width=128, max_height=128, related='image_1920', store=True)
```

``` xml
<record id="my_model_form" model="ir.ui.view">
    <field name="name">my.model.form</field>
    <field name="model">my.model</field>
    <field name="arch" type="xml">
        <form>
            <sheet>
                <group>
                    <field
                        name="image_1920"
                        class="oe_avatar"
                         options="{'preview_image': 'image_128', 'zoom': true}"
                     />
                </group>
            </sheet>
        </form>
    </field>
</record>
```

In the example above we have two fields, one for the original image and
one for a thumbnail. As the thumbnail is defined as a related stored
field it's automatically generated from the original image, resized at
the given size and stored in the database. The thumbnail is then used as
a preview image for the original image in the form view. The main
advantage of this approach is that the original image is not loaded in
the form view and the thumbnail is used instead, which is much smaller
in size and faster to load. The 'zoom' option allows the user to see the
original image in a popup when clicking on the thumbnail.

For convenience, the 'fs_image' module also provides a 'FSImageMixin'
mixin class that can be used to add the 'image' and 'image_medium'
fields to a model. It only define the medium thumbnail as a 128x128px
image since it's the most common use case. When using an image field in
a model, it's recommended to use this mixin class in order ensure that
the 'image_medium' field is always defined. A good practice is to use
the image_medium field as a preview image for the image field in the
form view to avoid to overload the form view with a large image and
consume too much bandwidth.

``` python
from odoo import models

class MyModel(models.Model):
    _name = 'my.model'
    _inherit = ['fs_image.mixin']
```

``` xml
<record id="my_model_form" model="ir.ui.view">
    <field name="name">my.model.form</field>
    <field name="model">my.model</field>
    <field name="arch" type="xml">
        <form>
            <sheet>
                <group>
                    <field
                        name="image"
                        class="oe_avatar"
                        options="{'preview_image': 'image_medium', 'zoom': true}"
                    />
                </group>
            </sheet>
        </form>
    </field>
</record>
```
