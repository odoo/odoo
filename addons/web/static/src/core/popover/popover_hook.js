/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";

import { onWillUnmount, status, useComponent } from "@odoo/owl";

export function usePopover() {
    const removeFns = new Set();
    const service = useService("popover");
    const component = useComponent();

    onWillUnmount(function () {
        for (const removeFn of removeFns) {
            removeFn();
        }
        removeFns.clear();
    });
    return {
        /**
         * Signals the manager to add a popover.
         *
         * @param {string | HTMLElement} target
         * @param {typeof import("@odoo/owl").Component} Component
         * @param {object} props
         * @param {import("@web/core/popover/popover_service").PopoverServiceAddOptions} [options]
         * @returns {() => void}
         */
        add(target, Component, props, options = {}) {
            const newOptions = Object.create(options);
            newOptions.onClose = function () {
                removeFns.delete(removeFn);
                if (options.onClose && status(component) !== "destroyed") {
                    options.onClose();
                }
            };

            const removeFn = service.add(target, Component, props, newOptions);
            removeFns.add(removeFn);
            return removeFn;
        },
    };
}
