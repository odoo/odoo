/** @odoo-module **/
import { registry } from "@web/core/registry";
import { _lt } from "../core/l10n/translation";

const { Component, useState } = owl;
const fieldRegistry = registry.category("fields");

// -----------------------------------------------------------------------------
// FieldChar
// -----------------------------------------------------------------------------

export class FieldChar extends Component {
    onChange(ev) {
        this.props.record.update(this.props.name, ev.target.value);
    }
}
FieldChar.template = "web.FieldChar";
fieldRegistry.add("char", FieldChar);

// -----------------------------------------------------------------------------
// FieldText
// -----------------------------------------------------------------------------

export class FieldText extends Component {
    onChange(ev) {
        this.props.record.update(this.props.name, ev.target.value);
    }
}
FieldText.template = "web.FieldText";
fieldRegistry.add("text", FieldText);

// -----------------------------------------------------------------------------
// FieldBoolean
// -----------------------------------------------------------------------------

export class FieldBoolean extends Component {
    onChange(ev) {
        this.props.record.update(this.props.name, ev.target.checked);
    }
}
FieldBoolean.template = "web.FieldBoolean";
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
const placeholder = "/web/static/img/placeholder.png";
export class FieldImage extends Component {
    setup() {
        if (this.props.value) {
            const magic = fileTypeMagicWordMap[this.props.value[0] || "png"];
            this.url = `data:image/${magic};base64,${this.props.value}`;
        } else {
            this.url = placeholder;
        }
    }
}
FieldImage.template = "web.FieldImage";
fieldRegistry.add("image", FieldImage);

// -----------------------------------------------------------------------------
// FieldSelection
// -----------------------------------------------------------------------------

export class FieldSelection extends Component {
    setup() {
        const field = this.props.record.fields[this.props.name];
        this.selection = Object.fromEntries(field.selection);
    }

    get value() {
        return this.props.record.data[this.props.name];
    }

    get string() {
        return this.value ? this.selection[this.value] : "";
    }
}
FieldSelection.template = "web.FieldSelection";
fieldRegistry.add("selection", FieldSelection);

// -----------------------------------------------------------------------------
// FieldColorPicker
// -----------------------------------------------------------------------------

export class FieldColorPicker extends Component {}
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

// -----------------------------------------------------------------------------
// FieldColorPicker
// -----------------------------------------------------------------------------

export class FieldPriority extends FieldSelection {
    setup() {
        super.setup();

        this.state = useState({ index: -1 });
    }

    get index() {
        return Math.max(this.state.index, Object.keys(this.selection).indexOf(this.value));
    }

    onStarClicked(value) {
        const actualValue = this.value === value ? Object.keys(this.selection)[0] : value;
        this.props.record.update(this.props.name, actualValue);
    }
}
FieldPriority.template = "web.FieldPriority";
fieldRegistry.add("priority", FieldPriority);
