import { browser } from "@web/core/browser/browser";
import { useBus, useService } from "@web/core/utils/hooks";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { useOwnDebugContext } from "@web/core/debug/debug_context";
import { ActionContainer } from "@web/webclient/actions/action_container";
import { Component, onMounted, useExternalListener, useState } from "@odoo/owl";

export class ProjectSharingWebClient extends Component {
    static props = {};
    static components = { ActionContainer, MainComponentsContainer };
    static template = "project.ProjectSharingWebClient";

    setup() {
        this.actionService = useService("action");
        useOwnDebugContext({ categories: ["default"] });
        this.state = useState({
            fullscreen: false,
        });
        useBus(this.env.bus, "ACTION_MANAGER:UI-UPDATED", (mode) => {
            if (mode !== "new") {
                this.state.fullscreen = mode === "fullscreen";
            }
        });
        onMounted(() => {
            this.loadRouterState();
            // the chat window and dialog services listen to 'web_client_ready' event in
            // order to initialize themselves:
            this.env.bus.trigger("WEB_CLIENT_READY");
        });
        useExternalListener(window, "click", this.onGlobalClick, { capture: true });
    }

    async loadRouterState() {
        // ** url-retrocompatibility **
        const stateLoaded = await this.actionService.loadState();

        // Scroll to anchor after the state is loaded
        if (stateLoaded) {
            if (browser.location.hash !== "") {
                try {
                    const el = document.querySelector(browser.location.hash);
                    if (el !== null) {
                        el.scrollIntoView(true);
                    }
                } catch {
                    // do nothing if the hash is not a correct selector.
                }
            }
        }
    }

    /**
     * @param {MouseEvent} ev
     */
    onGlobalClick(ev) {
        // When a ctrl-click occurs inside an <a href/> element
        // we let the browser do the default behavior and
        // we do not want any other listener to execute.
        if (
            (ev.ctrlKey || ev.metaKey) &&
            !ev.target.isContentEditable &&
            ((ev.target instanceof HTMLAnchorElement && ev.target.href) ||
                (ev.target instanceof HTMLElement && ev.target.closest("a[href]:not([href=''])")))
        ) {
            ev.stopImmediatePropagation();
            return;
        }
    }
}
