/** @odoo-module **/

import { registry } from "../registry";
import { PopoverContainer } from "./popover_container";

const { EventBus } = owl;

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
         * @param {string | HTMLElement}    target
         * @param {any}                     Component
         * @param {Object}                  props
         * @param {Object}                  [options]
         * @param {boolean}                 [options.closeOnClickAway=true]
         * @param {function(): void}        [options.onClose]
         * @param {string}                  [options.popoverClass]
         * @param {string}                  [options.position]
         * @param {function}                [options.onPositioned]
         * @returns {function(): void}
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
