import { useAutofocus } from "@web/core/utils/hooks";
import { ModelFieldSelectorPopover } from "@web/core/model_field_selector/model_field_selector_popover";
import { Component, useState, onWillStart } from "@odoo/owl";
import { user } from "@web/core/user";

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

        onWillStart(async () => {
            this.isTemplateEditor = await user.hasGroup("mail.group_mail_template_editor");
        });
    }

    filter(fieldDef, path) {
        const fullPath = "object" + (path ? `.${path}` : "") + `.${fieldDef.name}`;

        // See: /mail/models/ir_qweb.py
        const allowedQwebExpressions = [
            "object.name",
            "object.contact_name",
            "object.partner_id",
            "object.partner_id.name",
            "object.user_id",
            "object.user_id.name",
            "object.user_id.signature",
        ];
        if (!this.isTemplateEditor && !allowedQwebExpressions.includes(fullPath)) {
            return false;
        }
        return !["one2many", "boolean", "many2many"].includes(fieldDef.type) && fieldDef.searchable;
    }
    closeFieldSelector() {
        this.state.isPathSelected = true;
    }
    setPath(path, fieldInfo) {
        this.state.path = path;
        this.state.fieldName = fieldInfo && fieldInfo.string;
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
