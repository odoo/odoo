import { registry } from "@web/core/registry";
import { Plugin } from "../plugin";

export class BorderPlugin extends Plugin {
    static id = "border";
    static dependencies = ["style", "rules"];
    static shared = ["hasBorderWidth", "getBorderStyleInfo"];

    // TODO EGGMAIL:
    // need to move "filter_content_plugin" rules related to border here
    // and have a special ruleset for only border rules to isolate them

    hasBorderWidth(borderStyleInfo) {
        // TODO EGGMAIL
        // check if there is at least one border-edge-width with non-zero
        // value
    }

    getBorderStyleInfo(styleInfo, referenceNode) {
        // TODO EGGMAIL
        // need to apply border rules to styleInfo and then translate
        // border shorthands to their longhand counterparts
    }
}

registry.category("mail-html-conversion-core-plugins").add(BorderPlugin.id, BorderPlugin);
