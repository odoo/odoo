// @ts-check

/** @module @web/ui/overlay/overlay_service - Low-level service for adding/removing overlay components (popovers, dialogs, effects) */

import { markRaw, reactive } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { OverlayContainer } from "@web/ui/overlay/overlay_container";

const mainComponents = registry.category("main_components");
const services = registry.category("services");

/**
 * @typedef {{
 *  env?: object;
 *  onRemove?: (params?: any) => void;
 *  sequence?: number;
 *  rootId?: string;
 * }} OverlayServiceAddOptions
 */

/**
 * Low-level service for adding/removing overlay components (popovers, dialogs, effects).
 *
 * Manages a reactive registry of overlay entries rendered by `OverlayContainer`.
 * Higher-level services (popover, dialog, bottom_sheet, effect) build on top of this.
 */
export const overlayService = {
    start() {
        let nextId = 0;
        const overlays = reactive({});

        mainComponents.add("OverlayContainer", {
            Component: OverlayContainer,
            props: { overlays },
        });

        const remove = async (
            id,
            onRemove = /** @type {(params?: any) => void} */ (() => {}),
            removeParams,
        ) => {
            if (id in overlays) {
                try {
                    await onRemove(removeParams);
                } finally {
                    delete overlays[id];
                }
            }
        };

        /**
         * @param {typeof Component} component
         * @param {object} props
         * @param {OverlayServiceAddOptions} [options]
         * @returns {() => void}
         */
        const add = (component, props, options = {}) => {
            const id = ++nextId;
            const removeCurrentOverlay = (removeParams) =>
                remove(id, options.onRemove, removeParams);
            overlays[id] = {
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

        return { add, overlays };
    },
};

services.add("overlay", overlayService);
