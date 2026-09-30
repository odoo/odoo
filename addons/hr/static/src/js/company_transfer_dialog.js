import { Component, signal, t, useProps } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";
import { Many2OneField, buildM2OFieldDescription } from "@web/views/fields/many2one/many2one_field";

export class CompanyModificationDialog extends Component {
    static template = "hr.CompanyModificationDialog";
    static components = { Dialog };

    props = useProps({
        confirmDuplicate: t.function(),
        confirmDuplicateArchive: t.function(),
        close: t.function(),
    });

    onDuplicateClick = async () => {
        await this.props.confirmDuplicate();
        this.props.close();
    };
    onDuplicateArchiveClick = async () => {
        await this.props.confirmDuplicateArchive();
        this.props.close();
    };
    onDiscard = () => {
        this.props.close();
    };
}

export class CompanyTransferMany2OneField extends Many2OneField {
    inputReset = signal(null);

    setup() {
        super.setup();
        this.dialog = useService("dialog");
        this.orm = useService("orm");
        this.action = useService("action");
    }

    get m2oProps() {
        this.inputReset();
        return {
            ...super.m2oProps,
            update: (value, options) => this.onUpdate(value, options),
        };
    }

    onUpdate(value, options) {
        const record = this.props.record;
        const currentCompanyId = record.data.company_id?.id;
        const newCompanyId = value?.id;

        if (record.resId && currentCompanyId && newCompanyId && currentCompanyId !== newCompanyId) {
            this.dialog.add(
                CompanyModificationDialog,
                {
                    confirmDuplicate: async () => {
                        const action = await this.orm.call(
                            "hr.employee",
                            "action_duplicate_employee",
                            [[record.resId], newCompanyId]
                        );
                        await this.action.doAction(action);
                    },
                    confirmDuplicateArchive: async () => {
                        const action = await this.orm.call(
                            "hr.employee",
                            "action_duplicate_and_archive_employee",
                            [[record.resId], newCompanyId]
                        );
                        await this.action.doAction(action);
                    },
                },
                { onClose: () => signal.trigger(this.inputReset) }
            );
            return;
        }

        return record.update({ [this.props.name]: value }, options);
    }
}

registry.category("fields").add("company_transfer_m2o", {
    ...buildM2OFieldDescription(CompanyTransferMany2OneField),
});
