import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { Many2One, useMany2One } from "@web/views/fields/many2one/many2one";
import { buildM2OFieldDescription, Many2OneField } from "@web/views/fields/many2one/many2one_field";

export class ProjectMany2OneField extends Component {
    static template = "project.ProjectMany2OneField";
    static components = { Many2One };
    static props = { ...Many2OneField.props };

    setup() {
        this.m2o = useMany2One(() => this.props);
    }

    get m2oProps() {
        const p = this.m2o.computeProps();
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
