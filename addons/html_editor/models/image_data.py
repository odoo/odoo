from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ImageData(models.Model):
    _name = 'html_editor.image.data'
    _description = 'Image Data'

    res_model = fields.Char('Resource Model', required=True, readonly=True)
    res_field = fields.Char('Resource Field', required=True, readonly=True)
    res_id = fields.Many2oneReference('Resource ID', model_field='res_model', required=True, readonly=True)

    original_id = fields.Many2one('ir.attachment', string='Original (unoptimized, unresized) attachment')
    original_src = fields.Char(related='original_id.image_src', store=True)
    mimetype = fields.Char(help='Current mimetype of the image')
    original_mimetype = fields.Char(help='Mimetype of the image before a shape has been applied')
    mimetype_before_conversion = fields.Char(help='Mimetype of the image before the webp conversion')
    resize_width = fields.Char(help='The width of the image')
    gl_filter = fields.Char(help='The name of the filter applied on the image')
    quality = fields.Integer(default=75, help='The quality of the image')
    filter_options = fields.Char(help='The values of the custom filter applied on the image')
    # Shape options
    shape = fields.Char(help='The name of the shape applied on the image')
    shape_animation_speed = fields.Char(help='The speed of the shape applied on the image')
    shape_colors = fields.Char(help='The colors of the shape applied on the image')
    shape_flip = fields.Char(help='The directions in which the shape applied on the image have been flipped')
    shape_rotate = fields.Char(help='The tilt of the shape applied on the image')
    file_name = fields.Char(help='Name useful to recover the shape of the image')

    @api.constrains('res_model', 'res_field', 'res_id')
    def check_unique_record(self):
        for record in self:
            if self.search_count([('res_model', '=', record.res_model), ('res_field', '=', record.res_field), ('res_id', '=', record.res_id)]) > 1:
                raise ValidationError(_('There can be at most one image data linked to the field of a record'))

    def _get_image_data(self):
        """ Gets the data related to the image.

            Returns:
                dict: A dictionary of the data related to the image.
        """
        image_data_names = self._get_image_data_names()
        image_data_dict = {image_data_name: self[image_data_name] for image_data_name in image_data_names if self[image_data_name]}
        image_data_dict['original_id'] = self['original_id'].id
        image_data_dict['quality'] = self.quality
        return image_data_dict

    def _get_image_data_names(self):
        """ Gets the list of the names of the data stored in the record.

            Returns:
                list: A list of the names of the data stored in the record.

        """
        return self._get_removable_option_names() + [
            'original_src', 'mimetype', 'mimetype_before_conversion', 'filter_options',
        ]

    def _get_removable_option_names(self):
        """ Gets the list of the names of the image options that can be removed
        from the image. This is needed as they have to be removed each time the
        image options of an image are updated as they could have been removed
        during the edition. Indeed, in this case, the removed options will not
        be part of the options to update but they still should be removed from
        the record.

            Returns:
                list: a list of the names of the image options that can be
                      removed from the image.
        """
        return [
            'original_mimetype', 'resize_width', 'gl_filter', 'shape', 'shape_animation_speed',
            'shape_colors', 'shape_flip', 'shape_rotate', 'file_name',
        ]

    def _update_image_data(self, vals):
        """ Updates the data related to the image.

        Args:
            vals (dict): the new data of the image.

        Returns:
            bool: result of the write operation.
        """
        for option_to_remove in self._get_removable_option_names():
            # Remove some options before updating the record as they could have
            # been removed during the edition.
            self[option_to_remove] = ''
        return self.write(vals)
