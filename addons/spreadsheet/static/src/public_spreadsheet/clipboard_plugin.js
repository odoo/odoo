import { CommandResult, UIPlugin, registries } from "@odoo/o-spreadsheet";

const { statefulUIPluginRegistry } = registries;

class PublicClipboardPlugin extends UIPlugin {
    validators = {
        COPY: this.checkNoFigureSelected,
        CUT: this.checkNoFigureSelected,
    };

    checkNoFigureSelected() {
        if (this.getters.getSelectedFigureIds().length) {
            return CommandResult.Readonly;
        }
        return CommandResult.Success;
    }
}

statefulUIPluginRegistry.add("public_clipboard", PublicClipboardPlugin);
