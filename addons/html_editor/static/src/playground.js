/** @odoo-module */
import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useWysiwyg } from "./editor/wysiwyg";

export class Playground extends Component {
    static template = "html_editor.Playground";
    static props = ["*"];

    setup() {
        this.editor = useWysiwyg("html");
    }
}

registry.category("actions").add("html_editor.playground", Playground);
