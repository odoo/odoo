/** @odoo-module **/

import { useBus } from "../bus_hook";
import { registry } from "../registry";
import { useService } from "../service_hook";
import { Popover } from "./popover";

const { Component } = owl;
const { EventBus } = owl.core;
const { xml } = owl.tags;

export class KeyAlreadyExistsError extends Error {}

export class KeyNotFoundError extends Error {}

export class PopoverManager extends Component {
    setup() {
        // do not include popover params in state to keep original popover props
        this.popovers = {};

        const { bus } = useService("popover");
        useBus(bus, "ADD", this.addPopover);
        useBus(bus, "REMOVE", this.removePopover);
    }

    /**
     * @param {Object}                params
     * @param {string}                params.key
     * @param {string}                [params.content]
     * @param {any}                   [params.Component]
     * @param {Object}                [params.props]
     * @param {(key: string) => void} [params.onClose]
     * @param {boolean}               [params.keepOnClose=false]
     */
    addPopover(params) {
        if (params.key in this.popovers) {
            throw new KeyAlreadyExistsError(`PopoverManager already contains key "${params.key}"`);
        }

        this.popovers[params.key] = params;
        this.render();
    }
    /**
     * @param {string} key
     */
    removePopover(key) {
        if (!(key in this.popovers)) {
            throw new KeyNotFoundError(`PopoverManager does not contain key "${key}"`);
        }

        delete this.popovers[key];
        this.render();
    }

    /**
     * @param {string} key
     */
    onPopoverClosed(key) {
        if (!(key in this.popovers)) {
            // It can happen that the popover was removed manually just before this call
            return;
        }
        const popover = this.popovers[key];
        if (popover.onClose) {
            popover.onClose(key);
        }
        if (!popover.keepOnClose) {
            this.removePopover(key);
        }
    }
}
PopoverManager.components = { Popover }; // remove this as soon as Popover is globally registered
PopoverManager.template = xml`
  <div class="o_popover_manager">
    <div class="o_popover_container" />
    <t t-foreach="Object.values(popovers)" t-as="popover" t-key="popover.key">
      <t t-if="popover.Component">
        <t t-component="popover.Component"
          t-props="popover.props"
          t-on-popover-closed="onPopoverClosed(popover.key)"
        />
      </t>
      <t t-else="">
        <Popover
          t-props="popover.props"
          t-on-popover-closed="onPopoverClosed(popover.key)"
        >
          <t t-set-slot="content"><t t-esc="popover.content"/></t>
        </Popover>
      </t>
    </t>
  </div>
`;

registry.category("main_components").add("PopoverManager", {
    Component: PopoverManager,
});

export const popoverService = {
    start() {
        let nextId = 0;
        const bus = new EventBus();
        return {
            bus,
            /**
             * Signals the manager to add a popover.
             *
             * @param {Object}                params
             * @param {string}                [params.key]
             * @param {string}                [params.content]
             * @param {any}                   [params.Component]
             * @param {Object}                [params.props]
             * @param {(key: string) => void} [params.onClose]
             * @param {boolean}               [params.keepOnClose=false]
             * @returns {string}
             */
            add(params) {
                if (!("key" in params)) {
                    params.key = `popover_${nextId}`;
                    nextId += 1;
                }
                bus.trigger("ADD", params);
                return params.key;
            },
            /**
             * Signals the manager to remove the popover with key = `key`.
             *
             * @param {string} key
             */
            remove(key) {
                bus.trigger("REMOVE", key);
            },
        };
    },
};

registry.category("services").add("popover", popoverService);
