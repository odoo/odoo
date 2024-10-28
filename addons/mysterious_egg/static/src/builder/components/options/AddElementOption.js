import { Component } from "@odoo/owl";
import { defaultOptionComponents } from "../defaultComponents";

export class AddElementOption extends Component {
    static template = "mysterious_egg.AddElementOption";
    static components = {
        ...defaultOptionComponents,
    };
    static props = {
        toolboxElement: Object,
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
