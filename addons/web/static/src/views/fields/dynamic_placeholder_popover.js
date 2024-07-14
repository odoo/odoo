/** @odoo-module **/

import { useAutofocus } from "@web/core/utils/hooks";
import { ModelFieldSelectorPopover } from "@web/core/model_field_selector/model_field_selector_popover";
import { Component, useState } from "@odoo/owl";

export class DynamicPlaceholderPopover extends Component {
    static template = "web.DynamicPlaceholderPopover";
    static components = {
        ModelFieldSelectorPopover,
    };
    static props = ["resModel", "validate", "close"];

    setup() {
        useAutofocus();
        this.state = useState({
            path: "",
            isPathSelected: false,
            defaultValue: "",
        });
    }

    filter(fieldDef) {
        return !["one2many", "boolean", "many2many"].includes(fieldDef.type) && fieldDef.searchable;
    }
    closeFieldSelector() {
        if (this.state.path) {
            this.state.isPathSelected = true;
            return;
        }
        this.props.close();
    }
    setPath(path) {
        this.state.path = path;
    }
    setDefaultValue(value) {
        this.state.defaultValue = value;
    }
    validate() {
        this.props.close();
        this.props.validate(this.state.path, this.state.defaultValue);
    }

    // @TODO should rework this to use hotkeys
    async onInputKeydown(ev) {
        switch (ev.key) {
            case "Enter": {
                this.validate();
                break;
            }
            case "Escape": {
                this.props.close();
                break;
            }
        }
    }
}
