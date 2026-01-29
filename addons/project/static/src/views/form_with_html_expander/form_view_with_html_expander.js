/** @odoo-module */

import { registry } from "@web/core/registry";
import { formView } from '@web/views/form/form_view';
import { FormRendererWithHtmlExpander } from './form_renderer_with_html_expander';

export const formViewWithHtmlExpander = {
    ...formView,
    Renderer: FormRendererWithHtmlExpander,
};

registry.category('views').add('form_description_expander', formViewWithHtmlExpander);
