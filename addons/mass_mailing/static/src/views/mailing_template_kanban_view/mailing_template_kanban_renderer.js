import { getStyleSheets } from "../../utils/iframe_assets";
import { KanbanRenderer, kanbanRendererProps } from "@web/views/kanban/kanban_renderer";
import { providePlugins, t, useProps, useScope } from "@odoo/owl";
import { MailingTemplateKanbanRecord } from "./mailing_template_kanban_record";
import { StyleSheetPlugin } from "./stylesheets_plugin";

export class MailingTemplateKanbanRenderer extends KanbanRenderer {
    static template = "mass_mailing.MailingTemplateKanbanRenderer";
    static components = {
        ...KanbanRenderer.components,
        KanbanRecord: MailingTemplateKanbanRecord,
    };
    props = useProps({ ...kanbanRendererProps, iframeRef: t.signal(t.ref()) });
    setup() {
        super.setup();
        const scope = useScope();
        providePlugins([StyleSheetPlugin], {
            styleSheetPromises: [
                getStyleSheets(scope, this.props.iframeRef(), "mass_mailing.assets_iframe_style"),
                getStyleSheets(
                    scope,
                    this.props.iframeRef(),
                    "mass_mailing.assets_mailing_template_kanban_card_shadowdom"
                ),
            ],
        });
    }
}
