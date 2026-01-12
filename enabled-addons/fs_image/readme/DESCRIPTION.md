This addon defines a new field **FSImage** to use in your models. It is
a subclass of the **FSFile** field and comes with the same features. It
extends the **FSFile** field with specific properties dedicated to
images. On the field definition, the following additional properties are
available:

- **max_width** (int): maximum width of the image in pixels (default:
  `0`, no limit)
- **max_height** (int): maximum height of the image in pixels (default:
  `0`, no limit)
- **verify_resolution** (bool):whether the image resolution should be
  verified to ensure it doesn't go over the maximum image resolution
  (default: `True`). See odoo.tools.image.ImageProcess for maximum image
  resolution (default: `50e6`).

On the field's value side, the value is an instance of a subclass of
odoo.addons.fs_file.fields.FSFileValue. It extends the class to allows
you to manage an alt_text for the image. The alt_text is a text that
will be displayed when the image cannot be displayed.
