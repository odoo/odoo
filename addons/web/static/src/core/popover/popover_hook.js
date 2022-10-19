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
         * @param {string | HTMLElement}    target
         * @param {any}                     Component
         * @param {Object}                  props
         * @param {Object}                  [options]
         * @param {boolean}                 [options.closeOnClickAway=true]
         * @param {function()}              [options.onClose]
         * @param {function()}              [options.preventClose]
         * @param {string}                  [options.popoverClass]
         * @param {string}                  [options.position]
         * @returns {function()}
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
