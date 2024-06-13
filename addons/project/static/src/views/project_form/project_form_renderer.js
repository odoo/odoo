import { ProjectChatter } from "@project/components/project_chatter/project_chatter";

import { FormRendererWithHtmlExpander } from "../form_with_html_expander/form_renderer_with_html_expander";

export class ProjectFormRenderer extends FormRendererWithHtmlExpander {
    setup() {
        super.setup();
        this.mailComponents = {
            ...this.mailComponents,
            Chatter: ProjectChatter,
        };
    }

    get htmlFieldQuerySelector() {
        return '.o_field_html[name="description"]';
    }
}
