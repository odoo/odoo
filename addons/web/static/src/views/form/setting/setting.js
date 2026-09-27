import { Component, t, useProps } from "@odoo/owl";
import { FormLabel } from "../form_label";
import { DocumentationLink } from "@web/views/widgets/documentation_link/documentation_link";
import { user } from "@web/core/user";

export const settingProps = {
    id: t.string().optional(),
    info: t.string().optional(),
    title: t.string().optional(),
    fieldId: t.string().optional(),
    help: t.string().optional(),
    fieldName: t.string().optional(),
    fieldInfo: t.object().optional(),
    class: t.string().optional(),
    record: t.object().optional(),
    documentation: t.string().optional(),
    string: t.string().optional(),
    addLabel: t.boolean(),
    companyDependent: t.boolean().optional(),
    slots: t.object().optional(),
};

export class Setting extends Component {
    static template = "web.Setting";
    static components = {
        FormLabel,
        DocumentationLink,
    };
    props = useProps(settingProps);

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
