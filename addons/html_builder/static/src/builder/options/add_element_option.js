import { Component } from "@odoo/owl";
import { defaultBuilderComponents } from "../builder_components/default_builder_components";
import { Button } from "../components/button";

export class AddElementOption extends Component {
    static template = "html_builder.AddElementOption";
    static components = {
        ...defaultBuilderComponents,
        Button,
    };
    static props = {};

    addText() {
        console.log("addText");
    }
    addImage() {
        console.log("addImage");
    }
    addButton() {
        console.log("addButton");
    }
}
