import { Component, t, useProps, useScope } from "@odoo/owl";
import { MailingTemplateKanbanRenderer } from "./mailing_template_kanban_renderer";
import { useViewButtons } from "@web/views/view_button/view_button_hook";

/**
 * A wrapper for the KanbanRender used to make smooth reload
 * of the renderer cards on each update.
 * This helps us avoid a full iframe reload, with all the stylesheet
 * load, on each update.
 */
export class MailingTemplateKanbanWrapper extends Component {
    static template = "mass_mailing.MailingTemplateKanbanWrapper";
    static components = { MailingTemplateKanbanRenderer };
    props = useProps({ kanbanRendererProps: t.signal(t.object()), iframeRef: t.signal(t.ref()) });

    setup() {
        this.scope = useScope();
        useViewButtons(this.props.iframeRef, {
            afterExecuteAction: () => {
                if (this.scope.isDestroyed()) {
                    return;
                }
                return this.props.kanbanRendererProps().list.model.root.load();
            },
        });
    }
}
