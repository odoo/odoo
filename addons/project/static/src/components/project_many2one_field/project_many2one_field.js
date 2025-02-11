import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { computeM2OProps, Many2One } from "@web/views/fields/many2one/many2one";
import { buildM2OFieldDescription, Many2OneField } from "@web/views/fields/many2one/many2one_field";

export class ProjectMany2OneField extends Component {
    static template = "project.ProjectMany2OneField";
    static components = { Many2One };
    static props = { ...Many2OneField.props };

    get m2oProps() {
        const p = computeM2OProps(this.props);
        if (!this.props.record.data.project_id && !this.props.record._isRequired("project_id")) {
            p.placeholder = _t("Private");
            p.cssClass = "private_placeholder";
        }
        return p;
    }
}

registry.category("fields").add("project", {
    ...buildM2OFieldDescription(ProjectMany2OneField),
});
