import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

class MovePlugin extends Plugin {
    static id = "mass_mailing.MovePlugin";
    static dependencies = ["move"];
    resources = {
        is_movable_selector: [
            {
                selector: ".o_mail_snippet_general",
                direction: "vertical",
            },
            {
                selector: ".row:not(.s_col_no_resize) > div",
                direction: "horizontal",
                exclude: ".s_showcase .row > div",
            },
        ],
    };
}

registry.category("mass_mailing-plugins").add(MovePlugin.id, MovePlugin);
