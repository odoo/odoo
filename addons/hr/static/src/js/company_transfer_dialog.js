/** @odoo-module **/

import { Component, useProps, t } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";
import { Many2One, computeM2OProps } from "@web/views/fields/many2one/many2one";
import {
    buildM2OFieldDescription,
    extractM2OFieldProps,
    many2OneFieldProps,
} from "@web/views/fields/many2one/many2one_field";

export class CompanyModificationDialog extends Component {
    static template = "hr.CompanyModificationDialog";
    static components = { Dialog };

    props = useProps({
        confirmDuplicate: t.function(),
        confirmDuplicateArchive: t.function(),
        cancel: t.function(),
        close: t.function(),
    });

    onDuplicateClick = () => {
        this.props.confirmDuplicate();
        this.props.close();
    };
    onDuplicateArchiveClick = () => {
        this.props.confirmDuplicateArchive();
        this.props.close();
    };
    onDiscard = () => {
        this.props.cancel();
        this.props.close();
    };
}

export class CompanyTransferMany2OneField extends Component {
    static template = "hr.CompanyTransferMany2OneField";
    static components = { Many2One };

    props = useProps({ ...many2OneFieldProps });

    setup() {
        this.dialog = useService("dialog");
        this.orm = useService("orm");
        this.action = useService("action");
    }

    get m2oProps() {
        return {
            ...computeM2OProps(this.props),
            update: (value) => this.onUpdate(value),
        };
    }

    async onUpdate(value) {
        const record = this.props.record;

        const currentCompany = record.data.company_id;
        let currentCompanyId = false;
        if (Array.isArray(currentCompany) && currentCompany.length > 0) {
            currentCompanyId =
                typeof currentCompany[0] === "object" ? currentCompany[0].id : currentCompany[0];
        } else if (currentCompany && typeof currentCompany === "object") {
            currentCompanyId = currentCompany.id;
        } else if (currentCompany) {
            currentCompanyId = currentCompany;
        }

        let newCompanyId = false;
        if (Array.isArray(value) && value.length > 0) {
            newCompanyId = typeof value[0] === "object" ? value[0].id : value[0];
        } else if (value && typeof value === "object") {
            newCompanyId = value.id;
        } else if (value) {
            newCompanyId = value;
        }

        if (record.resId && currentCompanyId && newCompanyId && currentCompanyId !== newCompanyId) {
            this.dialog.add(CompanyModificationDialog, {
                confirmDuplicate: async () => {
                    const action = await this.orm.call("hr.employee", "action_duplicate_employee", [
                        [record.resId],
                        newCompanyId,
                    ]);
                    this.action.doAction(action);
                },
                confirmDuplicateArchive: async () => {
                    const action = await this.orm.call(
                        "hr.employee",
                        "action_duplicate_and_archive_employee",
                        [[record.resId], newCompanyId]
                    );
                    this.action.doAction(action);
                },
                cancel: () => {},
                close: () => {},
            });
            return;
        }

        return record.update({ [this.props.name]: value });
    }
}

registry.category("fields").add("company_transfer_m2o", {
    ...buildM2OFieldDescription(CompanyTransferMany2OneField),
    extractProps: extractM2OFieldProps,
});
