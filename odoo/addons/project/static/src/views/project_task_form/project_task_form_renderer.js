/** @odoo-module */

import { FormRendererWithHtmlExpander } from "../form_with_html_expander/form_renderer_with_html_expander";

export class ProjectTaskFormRenderer extends FormRendererWithHtmlExpander {
    get htmlFieldQuerySelector() {
        return '.o_field_html[name="description"]';
    }
}
