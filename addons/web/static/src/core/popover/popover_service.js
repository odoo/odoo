/** @odoo-module **/

import { markRaw } from "@odoo/owl";
import { registry } from "../registry";
import { PopoverController } from "./popover_controller";

/**
 * @typedef {{
 *   closeOnClickAway?: boolean | (target: HTMLElement) => boolean;
 *   closeOnHoverAway?: boolean;
 *   closeOnEscape?: boolean;
 *   onClose?: () => void;
 *   popoverClass?: string;
 *   position?: import("@web/core/position_hook").Options["position"];
 *   onPositioned?: import("@web/core/position_hook").PositionEventHandler;
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
         * @param {object} props
         * @param {PopoverServiceAddOptions} [options]
         * @returns {() => void}
         */
        const add = (target, component, props, options = {}) => {
            const closeOnEscape = "closeOnEscape" in options ? options.closeOnEscape : true;
            const closeOnHoverAway = options.closeOnHoverAway || false;
            const closeOnClickAway =
                typeof options.closeOnClickAway === "function"
                    ? options.closeOnClickAway
                    : () => options.closeOnClickAway ?? true;

            const remove = overlay.add(
                PopoverController,
                {
                    target,
                    close: () => remove(),
                    closeOnClickAway,
                    closeOnHoverAway,
                    closeOnEscape,
                    component,
                    componentProps: markRaw(props),
                    ref: options.ref,
                    popoverProps: {
                        target,
                        class: options.popoverClass,
                        role: options.popoverRole,
                        position: options.position,
                        onPositioned: options.onPositioned,
                        fixedPosition: options.fixedPosition,
                        enableArrow: options.enableArrow,
                    },
                },
                { onRemove: options.onClose }
            );

            return remove;
        };

        return { add };
    },
};

registry.category("services").add("popover", popoverService);
