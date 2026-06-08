import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { computeM2OProps, Many2One } from "@web/views/fields/many2one/many2one";
import { buildM2OFieldDescription, Many2OneField } from "@web/views/fields/many2one/many2one_field";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";
import { user } from "@web/core/user";
import { Component } from "@odoo/owl";

export class SoLineCreateButton extends Component {
    static template = "sale_timesheet.SoLineCreateButton";
    static components = { Many2One };
    static props = { ...Many2OneField.props };

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
                form_view_ref: context.so_form_view_ref,
                default_company_id: context.default_company_id || user.activeCompany.id,
                default_user_id: user.userId,
                hide_pdf_quote_builder: true,
            },
            onRecordSaved: async (rec) => {
                const service_line_id = await rec.model.orm.call(
                    "sale.order",
                    "get_first_service_line",
                    [rec.resId]
                );
                record.update({ sale_line_id: { id: service_line_id[0] } });
            },
        });
    }

    get m2oProps() {
        return computeM2OProps(this.props);
    }
}

registry.category("fields").add("so_line_create_button", {
    ...buildM2OFieldDescription(SoLineCreateButton),
});
