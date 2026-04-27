/** @odoo-module **/

import { router, routerBus } from "@web/core/browser/router";
import { useBus, useService } from '@web/core/utils/hooks';
import { ActionContainer } from '@web/webclient/actions/action_container';
import { MainComponentsContainer } from "@web/core/main_components_container";
import { useOwnDebugContext } from "@web/core/debug/debug_context";
import { Component, onMounted, useExternalListener } from "@odoo/owl";

export class KnowledgePortalWebClient extends Component {
    static props = {};
    static components = { ActionContainer, MainComponentsContainer };
    static template = "knowledge.KnowledgePortalWebClient";

    setup() {
        window.parent.document.body.style.margin = "0"; // remove the margin in the parent body
        this.actionService = useService("action");
        useOwnDebugContext({ categories: ["default"] });
        useBus(routerBus, "ROUTE_CHANGE", this._showView);
        onMounted(() => { this._showView(); });
        useExternalListener(window, "keydown", this.onGlobalKeyDown, { capture: true });
    }

    /**
     * Loads the article specified in the URL hash (eg. /knowledge/article#id=42)
     */
    async _showView() {
        const isOnKnowledgeArticleFormView = () => {
            if (this.actionService.currentController) {
                const { action } = this.actionService.currentController;
                return action && action.xml_id === "knowledge.knowledge_article_action_form";
            }
            return false;
        };

        // When the user is already on the Knowledge form view, we can load
        // another record in the model to avoid reloading the sidebar.

        if (isOnKnowledgeArticleFormView() && router.current.resId) {
            this.env.bus.trigger("KNOWLEDGE:OPEN_ARTICLE", {
                id: router.current.resId,
            });
            return;
        }

        await this.actionService.doAction("knowledge.ir_actions_server_knowledge_home_page", {
            additionalContext: router.current.resId
                ? { res_id: router.current.resId }
                : {},
            stackPosition: "replaceCurrentAction",
        });
    }

    /**
     * Prevent opening the command palette when CTRL+K is pressed, as portal users cannot have
     * access to its features (searching users, menus, ...).
     */
    onGlobalKeyDown(event) {
        if (event.key === 'k' && (event.ctrlKey || event.metaKey)) {
            event.stopPropagation();
        }
    }
}
