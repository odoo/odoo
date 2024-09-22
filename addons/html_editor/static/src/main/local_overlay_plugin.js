import { Plugin } from "../plugin";

/**
 * This plugins provides a way to create a "local" overlays so that their
 * visibility is relative to the overflow of their ancestors.
 */
export class LocalOverlayPlugin extends Plugin {
    static name = "local-overlay";
    static shared = ["makeLocalOverlay"];

    setup() {
        this.localOverlayContainer = this.config.localOverlayContainers?.ref.el;
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
