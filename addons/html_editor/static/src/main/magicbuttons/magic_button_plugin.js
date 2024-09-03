import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";

export class MagicButtonPlugin extends Plugin {
    static name = "magic_buttons";
    static dependencies = ["selection"];
    static resources = (p) => {
        const resources = {
            onSelectionChange: p.updatePosition.bind(p),
            powerboxItems: [
                {
                    name: _t("More Options"),
                    description: _t("Open more options"),
                    category: "structure",
                    fontawesome: "fa-ellipsis-v",
                    action(dispatch) {
                        // Initiate the opening of the powerbox
                        // Maybe
                        // this.dependencies.openPowerbox(); // ?
                    },
                },
            ],
        };
        return resources;
    };
    setup() {}

    get magicButtonCommands() {
        return this.shared.powerboxItems;
    }

    updatePosition(p) {}
}
