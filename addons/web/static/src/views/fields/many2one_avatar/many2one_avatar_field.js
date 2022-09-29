/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Many2OneField } from "../many2one/many2one_field";

export class Many2OneAvatarField extends Many2OneField {}

Many2OneAvatarField.template = "web.Many2OneAvatarField";
Many2OneAvatarField.avatarTemplate = "web.Many2OneAvatarField.Avatar";

registry.category("fields").add("many2one_avatar", Many2OneAvatarField);
