/** @odoo-module  **/
const { Component, tags } = owl;

import "wowl.legacySetup";
import { ComponentAdapter } from "web.OwlCompatibility";
import * as legacySystrayMenu from "web.SystrayMenu";
import { systrayRegistry } from "../webclient/systray_registry";

class SystrayItemAdapter extends ComponentAdapter {
  constructor() {
    super(...arguments);
    this.env = Component.env;
  }
}

const legacySystrayMenuItems = legacySystrayMenu.Items;
// registers the legacy systray menu items from the legacy systray registry
// to the wowl one, but wrapped into Owl components
legacySystrayMenuItems.forEach((item, index) => {
  const name = `_legacy_systray_item_${index}`;
  class SystrayItem extends Component {
    constructor() {
      super(...arguments);
      this.Widget = item;
    }
  }
  SystrayItem.template = tags.xml`<SystrayItemAdapter Component="Widget" />`;
  SystrayItem.components = { SystrayItemAdapter };
  systrayRegistry.add(name, {
    name,
    Component: SystrayItem,
    sequence: item.prototype.sequence,
  });
});
