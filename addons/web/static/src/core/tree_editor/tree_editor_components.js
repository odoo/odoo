import { Component } from "@odoo/owl";
import { TagsList } from "@web/core/tags_list/tags_list";

export class Input extends Component {
    static props = ["value", "update", "startEmpty?"];
    static template = "web.TreeEditor.Input";

    setup() {
        const prefill = this.env.getInputPrefill();
        if (prefill) {
            this.props.update(prefill);
        }
    }
}

export class Select extends Component {
    static props = ["value", "update", "options", "addBlankOption?", "type?"];
    static template = "web.TreeEditor.Select";

    setup() {
        // We only try to prefill if the select is a selection field, not the operator list
        if (this.props.type === "value") {
            const prefill = this.env.getInputPrefill();
            // If there is a prefill, check if we have a similarily starting string to prefill the select field
            if (prefill) {
                for (const option of this.props.options) {
                    if (option[1].toLowerCase().startsWith(prefill.toLowerCase())) {
                        this.props.update(option[0])
                        break;
                    }
                }
            }
        }
    }

    deserialize(value) {
        return JSON.parse(value);
    }

    serialize(value) {
        return JSON.stringify(value);
    }
}

export class Range extends Component {
    static props = ["value", "update", "editorInfo"];
    static template = "web.TreeEditor.Range";

    update(index, newValue) {
        const result = [...this.props.value];
        result[index] = newValue;
        return this.props.update(result);
    }
}

export class List extends Component {
    static components = { TagsList };
    static props = ["value", "update", "editorInfo"];
    static template = "web.TreeEditor.List";

    get tags() {
        const { isSupported, stringify } = this.props.editorInfo;
        return this.props.value.map((val, index) => ({
            text: stringify(val),
            colorIndex: isSupported(val) ? 0 : 2,
            onDelete: () => {
                this.props.update([
                    ...this.props.value.slice(0, index),
                    ...this.props.value.slice(index + 1),
                ]);
            },
        }));
    }

    update(newValue) {
        return this.props.update([...this.props.value, newValue]);
    }
}
