/** @odoo-module */
import { Component } from "@odoo/owl";

export class ViewEditorSnackbar extends Component {
    static template = "web_studio.ViewEditor.Snackbar";
    static props = {
        operations: Object,
        saveIndicator: Object,
    };
}
