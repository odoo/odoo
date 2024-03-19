import { ProjectChatter } from "@project/components/project_chatter/project_chatter";

import { FormRendererWithHtmlExpander } from "@resource/views/form_with_html_expander/form_renderer_with_html_expander";

export class ProjectFormRenderer extends FormRendererWithHtmlExpander {
    setup() {
        super.setup();
        this.mailComponents = {
            ...this.mailComponents,
            Chatter: ProjectChatter,
        };
    }
}
