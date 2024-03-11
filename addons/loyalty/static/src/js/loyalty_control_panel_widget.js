/** @odoo-module **/

import { registry } from "@web/core/registry";
import { X2ManyField } from "@web/views/fields/x2many/x2many_field";

export class LoyaltyX2ManyField extends X2ManyField {};
LoyaltyX2ManyField.template = "loyalty.LoyaltyX2ManyField";

registry.category("fields").add("loyalty_one2many", LoyaltyX2ManyField);
