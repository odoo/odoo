// @ts-check

/** @module @web/fields/basic/html/html_field - Simple HTML field widget extending TextField for Html columns */

import { registry } from "@web/core/registry";
import { TextField, textField } from "@web/fields/basic/text/text_field";

export class HtmlField extends TextField {
    static template = "web.HtmlField";
}

export const htmlField = {
    ...textField,
    component: HtmlField,
};

registry.category("fields").add("html", htmlField);
