import { Component } from "@odoo/owl";
import { FormLabel } from "../form_label";
import { DocumentationLink } from "@web/views/widgets/documentation_link/documentation_link";
import { user } from "@web/core/user";

export class Setting extends Component {
    static template = "web.Setting";
    static components = {
        FormLabel,
        DocumentationLink,
    };
    static props = {
        id: { type: String, optional: true },
        info: { type: String, optional: true },
        title: { type: String, optional: true },
        fieldId: { type: String, optional: true },
        help: { type: String, optional: true },
        fieldName: { type: String, optional: true },
        fieldInfo: { type: Object, optional: true },
        class: { type: String, optional: true },
        record: { type: Object, optional: true },
        documentation: { type: String, optional: true },
        string: { type: String, optional: true },
        addLabel: { type: Boolean },
        companyDependent: { type: Boolean, optional: true },
        slots: { type: Object, optional: true },
    };

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
        return this.labelString && this.props.companyDependent && user.allowedCompanies.length > 1;
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
