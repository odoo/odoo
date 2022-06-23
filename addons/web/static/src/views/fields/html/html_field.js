/** @odoo-module **/

import { registry } from "@web/core/registry";
import { TextField } from "../text/text_field";

export class HtmlField extends TextField {}

HtmlField.template = "web.HtmlField";

registry.category("fields").add("html", HtmlField);
