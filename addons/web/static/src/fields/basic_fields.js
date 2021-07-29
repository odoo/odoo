/** @odoo-module **/
import { registry } from "@web/core/registry";
import { CheckBox } from "@web/core/checkbox/checkbox";
import { _lt } from "../core/l10n/translation";

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
// FieldBoolean
// -----------------------------------------------------------------------------

export class FieldBoolean extends Component {
    setup() {
        this.record = this.props.record;
        this.data = Boolean(this.record.data[this.props.name]);
    }
}

FieldBoolean.template = "web.FieldBoolean";
FieldBoolean.components = { CheckBox };

fieldRegistry.add("boolean", FieldBoolean);

// -----------------------------------------------------------------------------
// FieldImage
// -----------------------------------------------------------------------------

export const fileTypeMagicWordMap = {
    "/": "jpg",
    R: "gif",
    i: "png",
    P: "svg+xml",
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

// -----------------------------------------------------------------------------
// FieldColorPicker
// -----------------------------------------------------------------------------

export class FieldColorPicker extends Component {
    setup() {
        this.record = this.props.record;
        this.data = this.record.data[this.props.name] || "";
    }
}

FieldColorPicker.template = "web.FieldChar";
FieldColorPicker.RECORD_COLORS = [
    _lt("No color"),
    _lt("Red"),
    _lt("Orange"),
    _lt("Yellow"),
    _lt("Light blue"),
    _lt("Dark purple"),
    _lt("Salmon pink"),
    _lt("Medium blue"),
    _lt("Dark blue"),
    _lt("Fushia"),
    _lt("Green"),
    _lt("Purple"),
];

fieldRegistry.add("color_picker", FieldColorPicker);
