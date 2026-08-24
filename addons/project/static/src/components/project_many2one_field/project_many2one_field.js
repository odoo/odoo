import { Component, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { computeM2OProps, Many2One } from "@web/views/fields/many2one/many2one";
import {
    buildM2OFieldDescription,
    many2OneFieldProps,
} from "@web/views/fields/many2one/many2one_field";

export class ProjectMany2OneField extends Component {
    static template = "project.ProjectMany2OneField";
    static components = { Many2One };
    props = useProps({ ...many2OneFieldProps });

    get m2oProps() {
        const props = computeM2OProps(this.props);
        const { record } = this.props;
        props.cssClass = "w-100";
        if (!record.data.project_id && !record._isRequired("project_id")) {
            if (!record.data.is_template) {
                props.placeholder = _t("Private");
                props.cssClass += " private_placeholder";
            } else {
                props.placeholder = _t("All Projects");
            }
        }
        return props;
    }

    get labelRegularTask() {
        return _t("🔒 Private");
    }

    get labelTemplateTask() {
        return _t("All Projects");
    }
}

registry.category("fields").add("project", {
    ...buildM2OFieldDescription(ProjectMany2OneField),
    fieldDependencies: [{ name: "is_template", type: "boolean" }],
});
