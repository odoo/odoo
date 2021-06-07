/** @odoo-module **/

import { registry } from "../registry";
import { PopoverContainer } from "./popover_container";

const { EventBus } = owl.core;

export const popoverService = {
    start() {
        let nextId = 0;
        const bus = new EventBus();
        registry
            .category("main_components")
            .add("PopoverContainer", { Component: PopoverContainer, props: { bus } });
        return {
            /**
             * Signals the manager to add a popover.
             *
             * @param {string | HTMLElement}    target
             * @param {any}                     Component
             * @param {Object}                  props
             * @param {Object}                  [options]
             * @param {boolean}                 [options.closeOnClickAway=true]
             * @param {() => void}              [options.onClose]
             * @param {string}                  [options.popoverClass]
             * @param {string}                  [options.position]
             * @returns {() => void}
             */
            add(target, Component, props, options = {}) {
                const id = ++nextId;
                bus.trigger("ADD", {
                    id,
                    target,
                    Component,
                    props,
                    onClose: options.onClose,
                    position: options.position,
                    popoverClass: options.popoverClass,
                    closeOnClickAway: options.closeOnClickAway,
                });
                return () => {
                    bus.trigger("REMOVE", id);
                };
            },
        };
    },
};

registry.category("services").add("popover", popoverService);
