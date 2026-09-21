/** @odoo-module **/

import { Component, proxy, useEffect } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { CodeEditor } from "@web/core/code_editor/code_editor";
import { useService } from "@web/core/utils/hooks";

export class JsonCodeField extends Component {
    static template = "hr_payroll.JsonCodeField";
    static components = { CodeEditor };
    static props = { ...standardFieldProps };

    setup() {
        this.notification = useService("notification");
        this.state = proxy({});
        this.isDirty = false;
        useEffect(() => {
            const val = this.props.record.data[this.props.name];
            this.state.stringValue = val && typeof val === "object" ? JSON.stringify(val, null, 4) : (val || "");
        });
    }

    handleChange(newValue) {
        if (this.state.stringValue !== newValue) {
            this.isDirty = true;
        }
        this.state.stringValue = newValue;
    }

    async commitChanges() {
        if (!this.props.readonly && this.isDirty) {
            const val = this.state.stringValue.trim();
            if (!val) {
                await this.props.record.update({ [this.props.name]: false });
                this.isDirty = false;
                return;
            }
            
            try {
                const parsed = JSON.parse(val);
                await this.props.record.update({ [this.props.name]: parsed });
                this.isDirty = false;
            } catch (e) {
                this.notification.add(`Invalid JSON syntax: ${e.message}`, {
                    type: "danger",
                    title: "Configuration Error",
                });
            }
        }
    }
}

registry.category("fields").add("json_code", {
    component: JsonCodeField,
    supportedTypes: ["json"],
});
