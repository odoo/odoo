// @ts-check

/** @module @web/views/form/setting/setting - Individual setting row with label, help text, and company-dependent icon */

import { Component } from "@odoo/owl";
import { user } from "@web/services/user";
import { FormLabel } from "@web/views/form/form_label";
import { DocumentationLink } from "@web/views/widgets/documentation_link/documentation_link";

/** Individual setting row inside a form view, with label, help text, and company-dependent icon. */
export class Setting extends Component {
    static template = "web.Setting";
    static components = {
        FormLabel,
        DocumentationLink,
    };
    static props = {
        id: { type: String, optional: 1 },
        info: { type: String, optional: 1 },
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

    setup() {
        if (this.props.fieldName) {
            this.fieldType = this.props.record.fields[this.props.fieldName].type;
            if (this.props.fieldInfo.readonly === "True") {
                this.notMuttedLabel = true;
            }
        }
    }

    /** @returns {Record<string, boolean>} CSS class map for the setting box container */
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

    /** @returns {boolean} whether to show the company-dependent icon */
    get displayCompanyDependentIcon() {
        return (
            this.labelString &&
            this.props.companyDependent &&
            user.allowedCompanies.length > 1
        );
    }

    /** @returns {string} display label from props or field metadata */
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
