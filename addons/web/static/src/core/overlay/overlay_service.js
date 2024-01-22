/** @odoo-module **/

import { markRaw, reactive } from "@odoo/owl";
import { registry } from "../registry";

const servicesRegistry = registry.category("services");
const overlaysRegistry = registry.category("overlays");

/**
 * @typedef {{
 *  onRemove?: () => void;
 *  sequence?: number;
 * }} OverlayServiceAddOptions
 */

export const overlayService = {
    start() {
        let nextId = 0;
        const overlays = reactive({});

        const remove = (id, onRemove = () => {}) => {
            if (id in overlays) {
                onRemove();
                delete overlays[id];
            }
        };

        const _add = (id, component, props = {}, options = {}) => {
            const removeCurrentOverlay = () => remove(id, options.onRemove);
            overlays[id] = {
                id,
                component,
                props: markRaw(props),
                remove: removeCurrentOverlay,
                sequence: options.sequence ?? 50,
            };
            return removeCurrentOverlay;
        };

        /**
         * @param {typeof Component} component
         * @param {object} [props]
         * @param {OverlayServiceAddOptions} [options]
         * @returns {() => void}
         */
        const add = (component, props = {}, options = {}) => {
            return _add(++nextId, component, props, options);
        };

        for (const [key, value] of overlaysRegistry.getEntries()) {
            _add(key, value.component, value.props);
        }

        overlaysRegistry.addEventListener("UPDATE", (ev) => {
            const { operation, key, value } = ev.detail;
            switch (operation) {
                case "add": {
                    _add(key, value.component, value.props);
                    break;
                }
                case "delete": {
                    remove(key);
                    break;
                }
            }
        });

        return { add, overlays };
    },
};

servicesRegistry.add("overlay", overlayService);
