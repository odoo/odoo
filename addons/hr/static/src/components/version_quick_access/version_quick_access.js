import { Component, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Many2One, computeM2OProps } from "@web/views/fields/many2one/many2one";
import { buildM2OFieldDescription, Many2OneField } from "@web/views/fields/many2one/many2one_field";

export class VersionQuickAccess extends Component {
    static template = "hr.version_quick_access";
    static components = { Many2One };
    static props = { ...Many2OneField.props };

    setup() {
        this.action = useService("action");
        this.orm = useService("orm");
        onWillStart(async () => {
            this.globalVersionTemplates = this.props.record.data[this.props.name]?.id
                ? await this.orm.searchRead("hr.version", [["employee_id", "=", false]], ["id"])
                : undefined;
        });
    }

    get m2oProps() {
        const { record, name } = this.props;
        const contractTemplateId = record.data[name].id;
        const employeeId = this.props.record.data.employee_id?.id;
        const isGlobalVersionTemplates = (this.globalVersionTemplates || []).some(
            (template) => template.id === contractTemplateId
        );
        if (contractTemplateId && employeeId && !isGlobalVersionTemplates) {
            return {
                ...computeM2OProps(this.props),
                openRecordAction: () => this.openRecordInAction(),
            };
        }
        return computeM2OProps(this.props);
    }

    async openRecordInAction() {
        const employeeId = this.props.record.data.employee_id?.id;
        const versionId =
            this.props.record.data.contract_template_id?.id ||
            this.props.record.data.version_id?.id;

        if (employeeId && versionId) {
            const context = {
                ...this.props.context,
                version_id: versionId,
            };
            const action = await this.orm.call(
                "hr.employee",
                "get_formview_action",
                [[employeeId]],
                { context }
            );
            return this.action.doAction(action);
        }
    }
}

registry.category("fields").add("version_quick_access", {
    ...buildM2OFieldDescription(VersionQuickAccess),
});
