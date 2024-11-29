import { Component } from "@odoo/owl";
import { defaultOptionComponents } from "../components/defaultComponents";

export class AddElementOption extends Component {
    static template = "html_builder.AddElementOption";
    static components = {
        ...defaultOptionComponents,
    };
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
