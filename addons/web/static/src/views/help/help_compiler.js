import { append, createElement } from "@web/core/utils/xml";
import { CardCompiler } from "@web/views/card/card_compiler";
import { ViewCompiler } from "@web/views/view_compiler";

/**
 * Compiles the arch of a help view (the content displayed when a view has no
 * record) into an owl template. Supported features:
 *  - regular html, with the same owl directives as cards (t-if, t-out...)
 *  - `invisible` attributes, evaluated against the action context (no record)
 *  - `data`, the values returned by the `data_method` of the model (if set on
 *    the <help> node), available in owl directives and `invisible` attributes
 *  - <button>/<a> with type "object" or "action" (compiled into ViewButtons,
 *    executed on an empty recordset)
 *  - <widget name="..."/> (from the "view_widgets" registry, without record)
 *  - `action_help`, the help of the action, to insert with <t t-out="action_help"/>
 *
 * Groups are applied server-side, as for any view.
 */
export class HelpCompiler extends ViewCompiler {
    setup() {
        this.compilers.push({ selector: "help", fn: this.compileHelp, doNotCopyAttributes: true });
    }

    compileHelp(el, params) {
        const compiled = createElement("t");
        for (const child of el.childNodes) {
            append(compiled, this.compileNode(child, params));
        }
        return compiled;
    }

    compileWidget(el) {
        const widget = createElement("HelpWidget", {
            widgetInfo: `__comp__.helpArchInfo.widgetNodes['${el.getAttribute("widget_id")}']`,
        });
        if (el.hasAttribute("class")) {
            widget.setAttribute("className", `'${el.getAttribute("class")}'`);
        }
        return widget;
    }
}
HelpCompiler.OWL_DIRECTIVE_WHITELIST = CardCompiler.OWL_DIRECTIVE_WHITELIST;
