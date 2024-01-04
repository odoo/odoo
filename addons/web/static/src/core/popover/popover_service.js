/** @odoo-module **/

import { markRaw } from "@odoo/owl";
import { registry } from "../registry";
import { Popover, POPOVER_SYMBOL } from "@web/core/popover/popover";

/**
 * @typedef {{
 *   closeOnClickAway?: boolean | (target: HTMLElement) => boolean;
 *   onClose?: () => void;
 *   popoverClass?: string;
 *   animation?: Boolean;
 *   arrow?: Boolean;
 *   position?: import("@web/core/position/position_hook").UsePositionOptions["position"];
 *   fixedPosition?: boolean;
 *   onPositioned?: import("@web/core/position/position_hook").UsePositionOptions["onPositioned"];
 * }} PopoverServiceAddOptions
 */

export const popoverService = {
    dependencies: ["overlay"],
    start(_, { overlay }) {
        /**
         * Signals the manager to add a popover.
         *
         * @param {HTMLElement} target
         * @param {typeof import("@odoo/owl").Component} component
         * @param {object} [props]
         * @param {PopoverServiceAddOptions} [options]
         * @returns {() => void}
         */
        const add = (target, component, props = {}, options = {}) => {
            const closeOnClickAway =
                typeof options.closeOnClickAway === "function"
                    ? options.closeOnClickAway
                    : () => options.closeOnClickAway ?? true;
            const remove = overlay.add(
                Popover,
                {
                    target,
                    close: () => remove(),
                    closeOnClickAway,
                    subPopovers: options[POPOVER_SYMBOL],
                    component,
                    componentProps: markRaw(props),
                    class: options.popoverClass,
                    animation: options.animation,
                    arrow: options.arrow,
                    position: options.position,
                    onPositioned: options.onPositioned,
                    fixedPosition: options.fixedPosition,
                },
                { onRemove: options.onClose }
            );

            return remove;
        };

        return { add };
    },
};

registry.category("services").add("popover", popoverService);
