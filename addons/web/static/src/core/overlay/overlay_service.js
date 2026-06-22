import { assertType, markRaw, Plugin, plugin, proxy, t } from "@odoo/owl";
import { registry } from "../registry";
import { OverlayContainer } from "./overlay_container";
import { services } from "@web/core/services";

const overlayServiceAddOptions = t.object({
   env: t.object().optional(),
   onRemove: t.function().optional(),
   sequence: t.number().optional(),
   rootId: t.string().optional(),
});

export class OverlayPlugin extends Plugin {
    /**
     * @private
     * @type {number}
     */
    nextId = 0;
    overlays = proxy({});

    setup() {
        registry.category("main_components").add("OverlayContainer", {
            Component: OverlayContainer,
            props: { overlays: this.overlays },
        });
    }

    /**
     * @param {typeof Component} component
     * @param {object} props
     * @param {overlayServiceAddOptions} [options]
     * @returns {(any) => void}
     */
    add(component, props, options = {}) {
        assertType(options, overlayServiceAddOptions);

        const remove = async (id, onRemove = () => {
        }, removeParams) => {
            if (id in this.overlays) {
                await onRemove(removeParams);
                delete this.overlays[id];
            }
        };

        const id = ++this.nextId;
        const removeCurrentOverlay = (removeParams) =>
            remove(id, options.onRemove, removeParams);
        this.overlays[id] = {
            id,
            component,
            env: options.env && markRaw(options.env),
            props,
            remove: removeCurrentOverlay,
            sequence: options.sequence ?? 50,
            rootId: options.rootId,
        };
        return removeCurrentOverlay;
    };
}

services.add(OverlayPlugin);

/**
 * -----------------------------------------------------------------------------
 * @todo owl3 migration
 * temporary - to remove when all use of the overlay service are removed
 * -----------------------------------------------------------------------------
 */
registry.category("services").add("overlay", {
    start() {
        return plugin(OverlayPlugin);
    }
});