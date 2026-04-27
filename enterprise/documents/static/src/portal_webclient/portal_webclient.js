/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { ActionContainer } from "@web/webclient/actions/action_container";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { Component, onMounted } from "@odoo/owl";

export class PortalWebclientWebClient extends Component {
    static props = {};
    static components = { ActionContainer, MainComponentsContainer };
    static template = "documents.PortalWebclientWebClient";

    setup() {
        this.action = useService("action");
        this.orm = useService("orm");
        this.view = useService("view");
        this.documentService = useService("document.document");
        const initData = this.documentService.initData;
        onMounted(async () => {
            const action = await this.action.loadAction("documents.document_action_portal");
            action.path = "documents"; // To get the standard URL
            this.action.doAction(action, {
                additionalContext: initData["folder_id"]
                    ? { searchpanel_default_folder_id: initData["folder_id"] }
                    : {},
                stackPosition: "replaceCurrentAction",
            });
        });
    }
}
