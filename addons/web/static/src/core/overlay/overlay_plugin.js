import {
    applyDefaults,
    assertType,
    Component,
    Plugin,
    Resource,
    t,
    untrack,
    usePlugin,
} from "@odoo/owl";
import { registry } from "../registry";
import { services } from "@web/core/services";

const OverlayOptionsSchema = t.object({
    scope: t.object().optional(),
    onRemove: t.function().optional(),
    sequence: t.number().optional(50),
    rootId: t.string().optional(),
});

const OverlayItemSchema = t.object({
    id: t.number(),
    component: t.constructor(Component),
    scope: t.object().optional(),
    props: t.object(),
    rootId: t.string().optional(),
    remove: t.function(),
});

export class OverlayPlugin extends Plugin {
    /**
     * @private
     */
    nextId = 0;
    overlays = new Resource({
        name: "overlays",
        validation: OverlayItemSchema,
    });

    /**
     * @param {typeof Component} component
     * @param {object} props
     * @param {OverlayOptionsSchema} [options]
     * @returns {() => Promise<void>}
     */
    add(component, props, options = {}) {
        return untrack(() => {
            assertType(options, OverlayOptionsSchema);
            options = applyDefaults(options, OverlayOptionsSchema);

            const overlay = {
                id: ++this.nextId,
                component,
                scope: options.scope,
                props,
                rootId: options.rootId,
                remove: async (removeParams) => {
                    if (this.overlays.has(overlay)) {
                        await options.onRemove?.(removeParams);
                        this.overlays.delete(overlay);
                    }
                },
            };
            this.overlays.add(overlay, { sequence: options.sequence });
            return overlay.remove;
        });
    }
}

services.add(OverlayPlugin);

/**
 * -----------------------------------------------------------------------------
 * @todo owl3 migration
 * temporary - to remove when all use of the overlay service are removed
 * -----------------------------------------------------------------------------
 */
export const overlayService = {
    start() {
        return usePlugin(OverlayPlugin);
    },
};

registry.category("services").add("overlay", overlayService);
