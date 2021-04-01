/** @odoo-module **/
import { CommandPalette } from "./command_palette";
const { Component, hooks } = owl;
const { useExternalListener, useRef } = hooks;

/**
 * @typedef {import("./command_service").Command} Command
 */

export class CommandPaletteDialog extends Component {
  setup() {
    this.dialogRef = useRef("dialogRef");
    useExternalListener(window, "mousedown", this.onWindowMouseDown);
  }

  /**
   * Used to close ourself on outside click.
   */
  onWindowMouseDown(ev) {
    const element = ev.target.parentElement;
    const gotClickedInside = this.dialogRef.comp.modalRef.el.contains(element);
    if (!gotClickedInside) {
      this.trigger("dialog-closed");
    }
  }
}
CommandPaletteDialog.template = "wowl.CommandPaletteDialog";
CommandPaletteDialog.components = { CommandPalette };
