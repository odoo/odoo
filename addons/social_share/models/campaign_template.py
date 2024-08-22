# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import OrderedDict
import base64
from io import BytesIO
from PIL import Image

from odoo import api, fields, models

TEMPLATE_DIMENSIONS = (1200, 630)
TEMPLATE_RATIO = 40 / 21
FONTS = ['NotoSans-VF.ttf', 'NotoSans[wght].ttf', 'Cantarell-VF.otf']

class campaignTemplate(models.Model):
    _name = 'social.share.campaign.template'
    _description = 'Social Share Template'

    name = fields.Char(required=True)
    image = fields.Image(compute='_compute_image')
    model_id = fields.Many2one(
        'ir.model', domain=lambda self: [('model', 'in', self._get_valid_target_models())],
    )

    # similar templates where preserving elements with 'roles' makes sense
    variant_ids = fields.One2many('social.share.campaign.template', inverse_name='parent_variant_id')
    parent_variant_id = fields.Many2one('social.share.campaign.template', copy=False)

    layers = fields.One2many('social.share.template.render.element', inverse_name="template_id", copy=True)

    # doesn't seem necessary yet
    # cache_group = fields.One2many('cache.group')  # groups of elements of which the render result can be cached for reuse

    def _get_valid_target_models(self):
        return self.env['social.share.model.allow'].search([]).sudo().model_id.mapped('model')

    @api.depends('layers')
    def _compute_image(self):
        for campaign in self:
            campaign.image = base64.encodebytes(campaign._generate_image_bytes())

    def _generate_image_bytes(self, record=None, replacement_renderers=None):
        # build a list for subgraphs in order of dependency as:
        # [[parent, child, sub_child], ...]
        # this is inefficient but only a few simple dependency graphs are expected
        def get_acyclic_dependencies(layer, encountered_layers=None):
            encountered_layers = encountered_layers or []
            return [
                child_dependency + [layer]
                for child_layer in layer.required_element_ids
                for child_dependency in get_acyclic_dependencies(child_layer, encountered_layers + [layer])
                if child_layer not in encountered_layers
            ] + [[layer]]
        acyclic_dependencies = [dependency_graph for layer in self.layers for dependency_graph in get_acyclic_dependencies(layer)]
        # append smaller subgraphs
        for graph in acyclic_dependencies:
            for start_index in range(1, len(graph)):
                acyclic_dependencies.append(graph[start_index:])

        # prepare renderers
        renderer_from_layer = OrderedDict()
        record = record if record is not None else (self.env[self.model_id.model] if self.model_id else None)
        if isinstance(record, models.BaseModel):
            record = record.sudo()  # access rights should have been checked when creating the layers
        for layer in self.layers:
            if replacement_renderers and layer.role and replacement_renderers.get(layer.role):
                renderer = replacement_renderers[layer.role]
            else:
                renderer = layer._get_renderer()
            renderer_from_layer[layer] = renderer

        # determine hidden layers
        image_from_layer = OrderedDict()
        not_rendered_set = set()
        for layer, renderer in renderer_from_layer.items():
            hide_children = False
            if layer in not_rendered_set:
                hide_children = True
            layer_image = renderer.render_image(record=record)
            if layer_image is None:
                hide_children = True
            if hide_children:
                pop_ids = []
                for graph_id, dependency_graph in enumerate(acyclic_dependencies):
                    if dependency_graph[0] == layer:
                        for graph_element in dependency_graph:
                            not_rendered_set.add(graph_element)
                            pop_ids.append(graph_id)
                for index_nb, index in enumerate(pop_ids):
                    acyclic_dependencies.pop(index - index_nb)
            image_from_layer[layer] = (renderer.pos, layer_image)

        # assemble image
        canvas_image = Image.new('RGBA', TEMPLATE_DIMENSIONS, color=(0, 0, 0))
        for layer, (pos, image) in image_from_layer.items():
            if layer not in not_rendered_set and image is not None:
                canvas_image.paste(image, pos, image)

        canvas_image_bytes = BytesIO()
        canvas_image.convert('RGB').save(canvas_image_bytes, "PNG")
        return canvas_image_bytes.getvalue()
