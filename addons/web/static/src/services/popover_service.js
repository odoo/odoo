/** @odoo-module **/

import { useBus } from "../core/hooks";
import { mainComponentRegistry } from "../webclient/main_component_registry";
import { serviceRegistry } from "../webclient/service_registry";

const { Component } = owl;
const { EventBus } = owl.core;
const { useState } = owl.hooks;
const { xml } = owl.tags;

const bus = new EventBus();

export class KeyAlreadyExistsError extends Error {
  constructor(key) {
    super(`PopoverManager already contains key "${key}"`);
  }
}

export class KeyNotFoundError extends Error {
  constructor(key) {
    super(`PopoverManager does not contain key "${key}"`);
  }
}

export class PopoverManager extends Component {
  setup() {
    this.popovers = useState({});
    this.nextId = 0;

    useBus(bus, "ADD", this.addPopover);
    useBus(bus, "REMOVE", this.removePopover);
  }

  /**
   * @param {Object}    params
   * @param {string}    [params.key]
   * @param {string}    [params.content]
   * @param {any}       [params.Component]
   * @param {Object}    [params.props]
   * @param {Function}  [params.onClose]
   * @param {boolean}   [params.keepOnClose=false]
   */
  addPopover(params) {
    const key = params.key || this.nextId;
    if (this.popovers[key]) {
      throw new KeyAlreadyExistsError(key);
    }

    this.popovers[key] = Object.assign({ key }, params);
    this.nextId += 1;
  }
  /**
   * @param {string | number} key
   */
  removePopover(key) {
    if (!this.popovers[key]) {
      throw new KeyNotFoundError(key);
    }

    delete this.popovers[key];
  }

  /**
   * @param {string | number} key
   */
  onPopoverClosed(key) {
    if (this.popovers[key].onClose) {
      this.popovers[key].onClose();
    }
    if (!this.popovers[key].keepOnClose) {
      this.removePopover(key);
    }
  }
}
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

mainComponentRegistry.add("PopoverManager", PopoverManager);

export const popoverService = {
  deploy(env) {
    return {
      /**
       * Signals the manager to add a popover.
       *
       * @param {Object}    params
       * @param {string}    [params.key]
       * @param {string}    [params.content]
       * @param {any}       [params.Component]
       * @param {Object}    [params.props]
       * @param {Function}  [params.onClose]
       * @param {boolean}   [params.keepOnClose=false]
       */
      add(params) {
        bus.trigger("ADD", params);
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

serviceRegistry.add("popover", popoverService);
