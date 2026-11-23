/** @odoo-module **/

import { registry } from "@web/core/registry";
import { integerField } from "../integer/integer_field";

registry.category("fields").add("many2one_reference", integerField);
