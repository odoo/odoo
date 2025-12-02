import { registry } from "@web/core/registry";
import { formView } from "@web/views/form/form_view";
import { FormRendererWithHtmlExpander } from "./form_renderer_with_html_expander";
import { FormControllerWithHTMLExpander } from "./form_controller_with_html_expander";

export const formViewWithHtmlExpander = {
    ...formView,
    Controller: FormControllerWithHTMLExpander,
    Renderer: FormRendererWithHtmlExpander,
};

registry.category("views").add("form_description_expander", formViewWithHtmlExpander);
