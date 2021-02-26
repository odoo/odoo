/** @odoo-module **/

import { Dropdown } from "../components/dropdown/dropdown";
import { DropdownItem } from "../components/dropdown/dropdown_item";
import { useService } from "../core/hooks";

const { Component, hooks } = owl;

export class DebugManager extends Component {
  constructor(...args) {
    super(...args);
    this.debugFactories = {};
    this.debugService = useService("debug_manager");
    // Defined as arrow to be passed as prop
    // @ts-ignore
    this.beforeOpenDropdown = async () => {
      if (!this.accessRights) {
        this.accessRights = await this.debugService.getAccessRights();
      }
    };
    this.env.bus.on("DEBUG-MANAGER:NEW-ITEMS", this, (payload) => {
      const { inDialog, elementsId, elementsFactory } = payload;
      if (this.isInDialog === inDialog) {
        this.debugFactories[elementsId] = elementsFactory;
      }
    });
    this.env.bus.on("DEBUG-MANAGER:REMOVE-ITEMS", this, (payload) => {
      const { inDialog, elementsId } = payload;
      if (this.isInDialog === inDialog) {
        delete this.debugFactories[elementsId];
      }
    });
    if (!this.isInDialog) {
      this.debugFactories["global"] = () =>
        odoo.debugManagerRegistry.getAll().map((elFactory) => elFactory(this.env));
    }
  }

  get isInDialog() {
    return this.env.inDialog;
  }

  getElements() {
    if (Object.keys(this.debugFactories).length > 0) {
      const sortedElements = Object.values(this.debugFactories)
        .map((factory) => factory(this.accessRights))
        .reduce((acc, elements) => acc.concat(elements))
        .sort((x, y) => {
          const xSeq = x.sequence ? x.sequence : 1000;
          const ySeq = y.sequence ? y.sequence : 1000;
          return xSeq - ySeq;
        });
      return sortedElements;
    } else {
      return [];
    }
  }

  onDropdownItemSelected(ev) {
    ev.detail.payload.callback();
  }

  onClickOnTagA(ev) {
    if (!ev.ctrlKey) {
      ev.preventDefault();
    }
  }
}

DebugManager.debugElementsId = 1;
DebugManager.template = "wowl.DebugManager";
DebugManager.components = { Dropdown, DropdownItem };

export const debugManager = {
  name: "wowl.debug_mode_menu",
  Component: DebugManager,
  sequence: 100,
};

export function useDebugManager(elementsFactory) {
  const elementsId = DebugManager.debugElementsId++;
  const component = Component.current;
  const env = component.env;
  const payload = {
    elementsId,
    elementsFactory,
    inDialog: env.inDialog,
  };
  hooks.onMounted(() => {
    env.bus.trigger("DEBUG-MANAGER:NEW-ITEMS", payload);
  });
  hooks.onWillUnmount(() => {
    env.bus.trigger("DEBUG-MANAGER:REMOVE-ITEMS", payload);
  });
}
