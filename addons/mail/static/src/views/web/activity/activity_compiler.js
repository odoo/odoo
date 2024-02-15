import { createElement, extractAttributes } from "@web/core/utils/xml";
import { toInterpolatedStringExpression, ViewCompiler } from "@web/views/view_compiler";
import { toStringExpression } from "@web/views/utils";

export class ActivityCompiler extends ViewCompiler {
    /**
     * @override
     */
    compileField(el, params) {
        let compiled;
        if (el.hasAttribute("widget")) {
            compiled = super.compileField(el, params);
        } else {
            // fields without a specified widget are rendered as simple spans in activity records
            compiled = createElement("div", {
                "t-out": `record["${el.getAttribute("name")}"].value`,
            });
        }
        const classNames = [];
        const { bold, display, muted } = extractAttributes(el, ["bold", "display", "muted"]);
        if (display === "right") {
            classNames.push("float-end");
        }
        if (display === "full") {
            classNames.push("d-block", "text-truncate");
        } else {
            classNames.push("d-inline-block");
        }
        if (bold) {
            classNames.push("fw-bold");
        }
        if (muted) {
            classNames.push("text-muted");
        }
        if (classNames.length > 0) {
            const clsFormatted = el.hasAttribute("widget")
                ? toStringExpression(classNames.join(" "))
                : classNames.join(" ");
            compiled.setAttribute("class", clsFormatted);
        }

        const attrs = {};
        for (const attr of el.attributes) {
            attrs[attr.name] = attr.value;
        }

        if (el.hasAttribute("widget")) {
            const attrsParts = Object.entries(attrs).map(([key, value]) => {
                if (key.startsWith("t-attf-")) {
                    key = key.slice(7);
                    value = toInterpolatedStringExpression(value);
                } else if (key.startsWith("t-att-")) {
                    key = key.slice(6);
                    value = `"" + (${value})`;
                } else if (key.startsWith("t-att")) {
                    throw new Error("t-att on <field> nodes is not supported");
                } else if (!key.startsWith("t-")) {
                    value = toStringExpression(value);
                }
                return `'${key}':${value}`;
            });
            compiled.setAttribute("attrs", `{${attrsParts.join(",")}}`);
        }

        for (const attr in attrs) {
            if (attr.startsWith("t-") && !attr.startsWith("t-att")) {
                compiled.setAttribute(attr, attrs[attr]);
            }
        }

        return compiled;
    }
}

ActivityCompiler.OWL_DIRECTIVE_WHITELIST = [
    ...ViewCompiler.OWL_DIRECTIVE_WHITELIST,
    "t-name",
    "t-esc",
    "t-out",
    "t-set",
    "t-value",
    "t-if",
    "t-else",
    "t-elif",
    "t-foreach",
    "t-as",
    "t-key",
    "t-att.*",
    "t-call",
    "t-translation",
];
