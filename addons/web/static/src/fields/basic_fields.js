/** @odoo-module **/
import { registry } from "@web/core/registry";

const { Component } = owl;
const fieldRegistry = registry.category("fields");

// -----------------------------------------------------------------------------
// FieldChar
// -----------------------------------------------------------------------------

export class FieldChar extends Component {
    static template = "web.FieldChar";

    setup() {
        this.record = this.props.record;
        this.data = this.record.data[this.props.name] || "";
    }
}

fieldRegistry.add("char", FieldChar);

// -----------------------------------------------------------------------------
// FieldImage
// -----------------------------------------------------------------------------

const fileTypeMagicWordMap = {
    "/": "jpg",
    R: "gif",
    i: "png",
    P: "svg+xml"
};
export class FieldImage extends Component {
    static template = "web.FieldImage";

    setup() {
        this.record = this.props.record;
        this.data = this.record.data[this.props.name];
        const magic = fileTypeMagicWordMap[this.data[0] || "png"];
        this.url = `data:image/${magic};base64,${this.data}`;
    }
}

fieldRegistry.add("image", FieldImage);

// -----------------------------------------------------------------------------
// FieldSelection
// -----------------------------------------------------------------------------

export class FieldSelection extends Component {
    static template = "web.FieldChar";

    setup() {
        this.record = this.props.record;
        const fields = this.record.fields;
        const field = fields[this.props.name];
        const selection = Object.fromEntries(field.selection);
        const fieldValue = this.record.data[this.props.name];
        this.data = fieldValue ? selection[fieldValue] : "";
    }
}

fieldRegistry.add("selection", FieldSelection);
