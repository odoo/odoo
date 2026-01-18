import { Plugin } from "../plugin";

/**
 * @typedef { Object } LocalOverlayShared
 * @property { LocalOverlayPlugin['makeLocalOverlay'] } makeLocalOverlay
 */

/**
 * This plugins provides a way to create a "local" overlays so that their
 * visibility is relative to the overflow of their ancestors.
 */
export class LocalOverlayPlugin extends Plugin {
    static id = "localOverlay";
    static shared = ["makeLocalOverlay"];

    setup() {
        this.localOverlayContainer = this.config.localOverlayContainers?.ref.el;
        this.localOverlays = new Set();
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
            this.localOverlays.add(container);
        }
        return container;
    }

    destroy() {
        for (const container of this.localOverlays) {
            container.remove();
        }
        this.localOverlays.clear();
        super.destroy();
    }
}
