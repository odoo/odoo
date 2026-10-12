import { CommandResult, UIPlugin, registries } from "@odoo/o-spreadsheet";

const { statefulUIPluginRegistry } = registries;

class PublicClipboardPlugin extends UIPlugin {
    allowDispatch(cmd) {
        if (
            (cmd.type === "COPY" || cmd.type === "CUT") &&
            this.getters.getSelectedFigureIds().length
        ) {
            return CommandResult.Readonly;
        }
        return CommandResult.Success;
    }
}

statefulUIPluginRegistry.add("public_clipboard", PublicClipboardPlugin);
