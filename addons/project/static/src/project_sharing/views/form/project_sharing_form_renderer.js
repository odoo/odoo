import { FormRenderer } from "@web/views/form/form_renderer";

import { Chatter } from "@mail/chatter/web_portal_project/chatter";

export class ProjectSharingFormRenderer extends FormRenderer {
    static components = {
        ...FormRenderer.components,
        Chatter,
    };
}
