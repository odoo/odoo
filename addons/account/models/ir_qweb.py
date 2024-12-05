from markupsafe import Markup
from lxml import etree

from odoo import api, models
from odoo.modules import get_module_path
from odoo.tools.misc import file_open

class IrQweb(models.AbstractModel):
    """
    Extends QWEB to allow accounting edi to use qweb to render template from files.
    """
    _inherit = 'ir.qweb'

    @api.model
    def _render_document(self, xml_tree, values=None, document_builder=None, custom_renderer=None):
        """
        Render an xml tree using Qweb.

        When using files, we cannot use t-call directive. We have to use qweb to render the subtemplate.

        When using this function, 'builder' and 'render' are passed as additional values to qweb. This only applied when not using a custom_renderer.

        :param xml_tree: etree (see _get_xml_tree_from_file)
        :param dict values: template values to be used for rendering.
        :param document_builder: an abstract model containing function callable from template during qweb rendering to customize the template. Can be accessed using 'builder' inside the qweb comtext
        :param custom_renderer: a renderer to be passed as the 'render' function in the qweb context. A default one is provided if none is passed. This is only used when rendering sub templates
        """
        
        def render_tree(template_tree):
            """
            Used mainly to render subtemplates. This is the default template renderer for file templates
            The qweb context for rendering the sub templates 
            """
            if template_tree is None:
                return Markup()

            return self._render(template_tree, {
                **values,
                'builder': document_builder,
                'render': custom_renderer if custom_renderer else render_tree,
            })

        return render_tree(xml_tree)

    @api.model
    def _get_xml_tree_from_file(self, module, file):
        module_path = get_module_path(module)
        transaction_base_xml_file_path = f'{module_path}/documents/{file}'
        xml_file_data = file_open(transaction_base_xml_file_path, 'rb').read()
        return etree.fromstring(xml_file_data)
