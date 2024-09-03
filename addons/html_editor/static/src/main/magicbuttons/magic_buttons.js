import { Component } from "@odoo/owl";

export class MagicButtons extends Component {
    static template = "html_editor.MagicButtons";
    static props = { editor: { type: Object } };
    setup() {
        console.log("SetUp executed");
    }
}
