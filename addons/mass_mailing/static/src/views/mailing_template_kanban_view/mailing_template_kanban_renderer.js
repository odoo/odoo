import { getStyleSheets } from "../../util/assets_utils";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { onMounted, providePlugins, useScope } from "@odoo/owl";
import { MailingTemplateKanbanRecord } from "./mailing_template_kanban_record";
import { StylesheetsPlugin } from "./stylesheets_plugin";

export class MailingTemplateKanbanRenderer extends KanbanRenderer {
    static template = "mass_mailing.MailingTemplateKanbanRenderer";
    static components = {
        ...KanbanRenderer.components,
        KanbanRecord: MailingTemplateKanbanRecord,
    };
    setup() {
        const {
            promise: iframePromise,
            resolve: resolveIframe,
            reject: rejectIframe,
        } = Promise.withResolvers();
        const {
            promise: cardPromise,
            resolve: resolveCard,
            reject: rejectCard,
        } = Promise.withResolvers();

        const scope = useScope();
        providePlugins([StylesheetsPlugin], { iframePromise, cardPromise });
        onMounted(() => {
            const iframe = this.rootRef().ownerDocument.defaultView.frameElement;
            getStyleSheets(scope, iframe, "mass_mailing.assets_iframe_style").then(
                resolveIframe,
                rejectIframe
            );
            getStyleSheets(
                scope,
                iframe,
                "mass_mailing.assets_mailing_template_kanban_card_style"
            ).then(resolveCard, rejectCard);
        });
        super.setup();
    }
}
