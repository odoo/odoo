import { registry } from "@web/core/registry";
import { TextField, textField } from "../text/text_field";

export class HtmlField extends TextField {
    static template = "web.HtmlField";
}

export const htmlField = {
    ...textField,
    component: HtmlField,
};

registry.category("fields").add("html", htmlField);
