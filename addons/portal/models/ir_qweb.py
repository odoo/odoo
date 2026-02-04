# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup

from odoo import models
from odoo.models import BaseModel
from odoo.tools import is_html_empty, lazy
from odoo.tools.json import scriptsafe, json_default


def owl_props(value, fields=None, **extra):
    """Serialize a value to JSON props for owl-component.

    This helper function serializes Python objects (including ORM records) to
    JSON format suitable for passing as props to OWL components via the
    `<owl-component>` tag.

    Usage in QWeb templates::

        <owl-component name="my.component" t-att-props="owl_props({'key': value})"/>
        <owl-component name="my.component" t-att-props="owl_props(record, fields=['name', 'email'])"/>
        <owl-component name="my.component" t-att-props="owl_props(record, fields=['name'], extra_prop=True)"/>

    :param value: dict, ORM record, or other JSON-serializable value
    :param fields: For ORM records, optional list of field names to include.
                   Defaults to ['display_name'] for safety.
    :param extra: Additional key-value pairs to merge into props (for dict values)
    :return: JSON string safe for HTML attribute embedding
    """
    def serialize(obj, flds=None):
        if isinstance(obj, BaseModel):
            if not obj:
                return []
            read_fields = flds or ['display_name']
            if 'id' not in read_fields:
                read_fields = ['id'] + list(read_fields)
            return obj.read(read_fields)[0] if len(obj) == 1 else obj.read(read_fields)
        elif isinstance(obj, dict):
            return {k: serialize(v, flds) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [serialize(item, flds) for item in obj]
        return obj

    serialized = serialize(value, fields)
    if isinstance(serialized, dict):
        serialized.update(extra)
    elif extra:
        serialized = {'value': serialized, **extra}
    # Escape < and > for safe embedding in HTML script contexts
    json_str = scriptsafe.dumps(serialized, default=json_default)
    return json_str.replace('<', '\\u003c').replace('>', '\\u003e')


def owl_component(name, props=None, **attrs):
    """Generate an <owl-component> tag with properly serialized props.

    This helper generates complete owl-component markup that will be mounted
    by the PublicComponentInteraction class on the client side.

    Usage in QWeb templates::

        <t t-out="owl_component('portal.signature_form', {'callUrl': call_url})"/>
        <t t-out="owl_component('my.component', props, class_='my-class')"/>

    :param name: The component name registered in the public_components registry
    :param props: Dictionary of props to pass to the component
    :param attrs: Additional HTML attributes for the owl-component tag.
                  Trailing underscores are stripped (e.g., class_ -> class) and
                  remaining underscores are converted to hyphens (e.g., data_test -> data-test).
    :return: Markup-safe HTML string
    """
    attr_parts = [Markup('name="{}"').format(name)]
    if props:
        # Ensure JSON is treated as plain string for proper HTML escaping
        props_json = str(scriptsafe.dumps(props, default=json_default))
        attr_parts.append(Markup('props="{}"').format(props_json))
    for attr_name, attr_value in attrs.items():
        if attr_value is not None:
            # Strip trailing underscore (Python convention to avoid reserved words like class_)
            # then convert remaining underscores to hyphens (data_test -> data-test)
            html_name = attr_name.rstrip("_").replace("_", "-")
            attr_parts.append(Markup('{}="{}"').format(html_name, attr_value))
    return Markup('<owl-component {}></owl-component>').format(Markup(' ').join(attr_parts))


class IrQweb(models.AbstractModel):
    _inherit = "ir.qweb"

    def _prepare_frontend_environment(self, values):
        """ Returns ir.qweb with context and update values with portal specific
            value (required to render portal layout template)
        """
        irQweb = super()._prepare_frontend_environment(values)
        values.update(
            is_html_empty=is_html_empty,
            frontend_languages=lazy(irQweb.env['res.lang']._get_frontend),
            # OWL component helpers for embedding OWL components in server-rendered templates
            owl_props=owl_props,
            owl_component=owl_component,
        )
        for key in irQweb.env.context:
            if key not in values:
                values[key] = irQweb.env.context[key]

        return irQweb
