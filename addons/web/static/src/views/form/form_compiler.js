/** @odoo-module **/

import { registry } from "@web/core/registry";
import { ViewCompiler } from "../helpers/view_compiler";

const { Component, hooks, tags } = owl;
const { useComponent } = hooks;
const { xml } = tags;

const templateIds = Object.create(null);
const compilersRegistry = registry.category("form_compilers");

export class FormCompiler extends ViewCompiler {
    setup() {
        this.compilers = compilersRegistry.getAll();
    }
}
