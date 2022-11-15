/** @odoo-module **/

import { registry } from "../registry";
import { PopoverContainer } from "./popover_container";

import { EventBus } from "@odoo/owl";

/**
 * @typedef {{
 *   closeOnClickAway?: boolean;
 *   onClose?: () => void;
 *   popoverClass?: string;
 *   position?: import("@web/core/position_hook").Direction;
 *   onPositioned?: import("@web/core/position_hook").PositionEventHandler;
 *   preventClose?: () => void;
 * }} PopoverServiceAddOptions
 */

export const popoverService = {
    start() {
        let nextId = 0;
        const popovers = {};
        const bus = new EventBus();

        registry
            .category("main_components")
            .add("PopoverContainer", { Component: PopoverContainer, props: { bus, popovers } });

        /**
         * Signals the manager to add a popover.
         *
         * @param {string | HTMLElement} target
         * @param {typeof import("@odoo/owl").Component} Component
         * @param {object} props
         * @param {PopoverServiceAddOptions} [options]
         * @returns {() => void}
         */
        function add(target, Component, props, options = {}) {
            const id = ++nextId;
            const closeFn = () => close(id);
            const popover = {
                id,
                target,
                Component,
                props,
                close: closeFn,
                onClose: options.onClose,
                position: options.position,
                onPositioned: options.onPositioned,
                popoverClass: options.popoverClass,
                closeOnClickAway: options.closeOnClickAway,
                preventClose: options.preventClose,
            };
            popovers[id] = popover;
            bus.trigger("UPDATE");
            return closeFn;
        }

        function close(id) {
            if (id in popovers) {
                const popover = popovers[id];
                if (popover.onClose) {
                    popover.onClose();
                }
                delete popovers[id];
                bus.trigger("UPDATE");
            }
        }

        return { add };
    },
};

registry.category("services").add("popover", popoverService);
