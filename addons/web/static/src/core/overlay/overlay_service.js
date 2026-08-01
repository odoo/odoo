import { markRaw, reactive } from "@odoo/owl";
import { registry } from "../registry";
import { OverlayContainer } from "./overlay_container";

const mainComponents = registry.category("main_components");
const services = registry.category("services");

/**
 * @typedef {{
 *  env?: object;
 *  onRemove?: () => void;
 *  sequence?: number;
 *  rootId?: string;
 * }} OverlayServiceAddOptions
 */

export const overlayService = {
    start() {
        let nextId = 0;
        const overlays = reactive({});

        mainComponents.add("OverlayContainer", {
            Component: OverlayContainer,
            props: { overlays },
        });

        const remove = async (id, onRemove = () => {}, removeParams) => {
            if (id in overlays) {
                await onRemove(removeParams);
                delete overlays[id];
            }
        };

        const getDefaultSequence = () => {
            const overlaysStack = Object.values(overlays);
            return overlaysStack.length > 0 ? overlaysStack.at(-1).sequence + 0.001 : 50;
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
                sequence: options.sequence ?? getDefaultSequence(),
                rootId: options.rootId,
            };
            return removeCurrentOverlay;
        };

        return { add, overlays };
    },
};

services.add("overlay", overlayService);
