import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Many2OneField, many2OneField } from "@web/views/fields/many2one/many2one_field";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";
import { user } from "@web/core/user";

export class SoLineCreateButton extends Many2OneField {
    static template = "sale_timesheet.SoLineCreateButton";

    setup() {
        super.setup();
        this.dialogService = useService("dialog");
    }

    openSalesOrderDialog() {
        const { context, record } = this.props;
        this.dialogService.add(FormViewDialog, {
            title: "Create Sales Order",
            resModel: "sale.order",
            context: {
                ...context,
                default_company_id: context.default_company_id || user.activeCompany.id,
            },
            onRecordSaved: async (rec) => {
                const service_line_id = await rec.model.orm.call(
                    "sale.order",
                    "get_first_service_line",
                    [rec.resId]
                );
                record.update({ sale_line_id: service_line_id });
            },
        });
    }
}

export const soLineCreateButton = {
    ...many2OneField,
    component: SoLineCreateButton,
};

registry.category("fields").add("so_line_create_button", soLineCreateButton);
