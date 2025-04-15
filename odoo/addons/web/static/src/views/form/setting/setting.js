/** @odoo-module **/

import { session } from "@web/session";
import { Component } from "@odoo/owl";
import { FormLabel } from "../form_label";
import { DocumentationLink } from "@web/views/widgets/documentation_link/documentation_link";

export class Setting extends Component {
    setup() {
        if (this.props.fieldName) {
            this.fieldType = this.props.record.fields[this.props.fieldName].type;
            if (this.props.fieldInfo.readonly === "True") {
                this.notMuttedLabel = true;
            }
        }
    }

    get classNames() {
        const { class: _class } = this.props;
        const classNames = {
            o_setting_box: true,
            "col-12": true,
            "col-lg-6": true,
            [_class]: Boolean(_class),
        };

        return classNames;
    }

    get displayCompanyDependentIcon() {
        return (
            this.labelString && this.props.companyDependent && session.display_switch_company_menu
        );
    }

    get labelString() {
        if (this.props.string) {
            return this.props.string;
        }
        const label =
            this.props.record &&
            this.props.record.fields[this.props.fieldName] &&
            this.props.record.fields[this.props.fieldName].string;
        return label || "";
    }
}
Setting.components = {
    FormLabel,
    DocumentationLink,
};
Setting.template = "web.Setting";
Setting.props = {
    title: { type: String, optional: 1 },
    fieldId: { type: String, optional: 1 },
    help: { type: String, optional: 1 },
    fieldName: { type: String, optional: 1 },
    fieldInfo: { type: Object, optional: 1 },
    class: { type: String, optional: 1 },
    record: { type: Object, optional: 1 },
    documentation: { type: String, optional: 1 },
    string: { type: String, optional: 1 },
    addLabel: { type: Boolean },
    companyDependent: { type: Boolean, optional: 1 },
    slots: { type: Object, optional: 1 },
};
