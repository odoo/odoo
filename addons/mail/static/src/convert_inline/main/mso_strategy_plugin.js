import { Plugin } from "../plugin";
import { registry } from "@web/core/registry";

export class MsoStrategyPlugin extends Plugin {
    static id = "msoStrategy";
    static dependencies = ["dynamicStyleSheet"];

    // TODO EGGMAIL: replace background images with VML output
    // border in MSO can not be bigger than 8px

    setup() {
        this.addToStyleSheet("body *", {
            "-ms-text-size-adjust": "100%",
        });
        this.addToStyleSheet("table, td", {
            "mso-table-lspace": { value: "0pt", priority: "important" },
            "mso-table-rspace": { value: "0pt", priority: "important" },
        });
    }
}

registry.category("mail-html-conversion-main-plugins").add(MsoStrategyPlugin.id, MsoStrategyPlugin);
