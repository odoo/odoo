/** @odoo-module **/

import { registry } from "@web/core/registry";
import { ViewCompiler } from "../helpers/view_compiler";

const templateIds = Object.create(null);
const compilersRegistry = registry.category("form_compilers");

export class FormCompiler extends ViewCompiler {
    setup() {
        this.compilers = compilersRegistry.getAll();
    }
}
