import { Component, props, proxy } from "@odoo/owl";
import { kanbanRendererProps } from "@web/views/kanban/kanban_renderer";
import { MailingTemplateKanbanRenderer } from "./mailing_template_kanban_renderer";

/**
 * A wrapper for the KanbanRender used to make smooth reload
 * of the renderer cards on each update.
 * This helps us avoid a full iframe reload, with all the stylesheet
 * load, on each update.
 */
export class MailingTemplateKanbanWrapper extends Component {
    static template = "mass_mailing.MailingTemplateKanbanWrapper";
    static components = { MailingTemplateKanbanRenderer };
    props = props(kanbanRendererProps);

    setup() {
        this.state = proxy({ rendererKey: 0 });
    }

    /**
     * Increment the t-key of the renderer component
     * in order for OWL to reload a fresh component.
     */
    async reloadRenderer() {
        this.state.rendererKey++;
    }
}
