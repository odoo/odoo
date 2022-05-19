/** @odoo-module **/

import { extractAttributes } from "@web/core/utils/xml";
import { ViewCompiler } from "@web/views/helpers/view_compiler";

export class KanbanCompiler extends ViewCompiler {
    /**
     * @override
     */
    compileField(el, params) {
        const compiled = super.compileField(el, params);
        const classAttr = compiled.getAttribute("class") || "";
        const classSet = new Set();
        const { bold, display } = extractAttributes(el, ["bold", "display"]);
        if (display === "right") {
            classSet.add("float-right");
        } else if (display === "full") {
            classSet.add("o_text_block");
        }
        if (bold) {
            classSet.add("o_text_bold");
        }
        const classAttrs = [classAttr, `'${[...classSet].join(" ")}'`].filter(Boolean);
        compiled.setAttribute("class", classAttrs.join("+"));
        return compiled;
    }
}
