import { ancestors } from "@html_editor/utils/dom_traversal";
import { Plugin } from "../plugin";
import { throttleForAnimation } from "@web/core/utils/timing";

/**
 * This plugins provides a way to create a "local" overlays so that their
 * visibility is relative to the overflow of their ancestors.
 */
export class LocalOverlayPlugin extends Plugin {
    static name = "local-overlay";
    static shared = ["makeLocalOverlay"];
    /** @type { (p: LocalOverlayPlugin) => Record<string, any> } */
    static resources = (p) => ({
        onExternalHistorySteps: p.refreshOverlay.bind(p),
        historyResetFromSteps: p.refreshOverlay.bind(p),
    });

    handleCommand(commandName) {
        switch (commandName) {
            case "ADD_STEP":
                this.refreshOverlay();
                break;
        }
    }

    setup() {
        this.localOverlayContainer = this.config.getLocalOverlayContainer?.();
        this.refreshOverlay = throttleForAnimation(this.refreshOverlay.bind(this));
        this.resizeObserver = new ResizeObserver(this.refreshOverlay);
        this.resizeObserver.observe(this.document.body);
        this.resizeObserver.observe(this.editable);
        this.addDomListener(window, "resize", this.refreshOverlay);
        if (this.document.defaultView !== window) {
            this.addDomListener(this.document.defaultView, "resize", this.refreshOverlay);
        }

        const scrollableElements = [this.editable, ...ancestors(this.editable)].filter((node) => {
            const style = getComputedStyle(node);
            return style.overflowY === "auto" || style.overflowY === "scroll";
        });
        for (const scrollableElement of scrollableElements) {
            this.addDomListener(scrollableElement, "scroll", () => {
                this.refreshOverlay();
            });
        }
    }
    destroy() {
        super.destroy();
        this.resizeObserver.disconnect();
    }
    refreshOverlay() {
        this.resources.refreshOverlay?.forEach((cb) => cb());
    }
    /**
     * Make a local container to organise floating elements inside it's own
     * box and z-index isolation.
     *
     * @param {string} containerId An id to add to the container in order to make
     *              the container more visible in the devtool and potentially
     *              add css rules for the container and it's children.
     */
    makeLocalOverlay(containerId) {
        const container = this.document.createElement("div");
        container.className = `oe-local-overlay`;
        container.setAttribute("data-oe-local-overlay-id", containerId);
        if (this.localOverlayContainer) {
            this.localOverlayContainer.append(container);
        }
        return container;
    }
}
