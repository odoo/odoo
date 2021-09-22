/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { CommandPalette } from "./command_palette";

const { hooks } = owl;
const { useExternalListener } = hooks;

/**
 * @typedef {import("./command_service").Command} Command
 */

export class CommandPaletteDialog extends Dialog {
    setup() {
        super.setup();
        useExternalListener(window, "mousedown", this.onWindowMouseDown);
    }

    /**
     * Used to close ourself on outside click.
     */
    onWindowMouseDown(ev) {
        const element = ev.target.parentElement;
        const gotClickedInside = this.modalRef.el.contains(element);
        if (!gotClickedInside) {
            this.close();
        }
    }
}
CommandPaletteDialog.renderHeader = false;
CommandPaletteDialog.renderFooter = false;
CommandPaletteDialog.size = "modal-md";
CommandPaletteDialog.contentClass = "o_command_palette";
CommandPaletteDialog.bodyTemplate = "web.CommandPaletteDialogBody";
CommandPaletteDialog.components = Object.assign({}, Dialog.components, { CommandPalette });
