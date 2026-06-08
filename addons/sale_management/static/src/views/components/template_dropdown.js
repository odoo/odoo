import { Component, onWillStart, props, proxy, t } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog, deleteConfirmationMessage } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { user } from "@web/core/user";

export class SaleTemplateDropdown extends Component {
    static template = "sale_management.SaleTemplateDropdown";
    static components = {
        Dropdown,
        DropdownItem,
    };

    props = props({
        hotkey: t.string().optional("c"),
        newButtonClasses: t.string(),
        // `isDisabled` was only declared in `defaultProps`, but it is used in the template
        isDisabled: t.boolean().optional(false),
        record: t.object().optional(),
    });

    setup() {
        this.action = useService("action");
        this.dialogService = useService("dialog");
        this.orm = useService("orm");
        this.state = proxy({
            canManageTemplates: false,
            quotationTemplates: [],
        });
        onWillStart(this.onWillStart);
    }

    async onWillStart() {
        this.state.canManageTemplates = await user.hasGroup("sales_team.group_sale_manager");
        this.state.quotationTemplates = await this.orm.searchRead(
            "sale.order.template",
            [["template_type", "=", "quotation"]],
            ["id", "name"]
        ).catch(() => []);
    }

    async _saveIfNeeded() {
        if (!this.saveRecord) {
            return true;
        }
        return await this.saveRecord();
    }

    get saveRecord() {
        return this.props.record?.save?.bind(this.props.record);
    }

    get isFormView() {
        return this.env.config?.viewType === "form";
    }

    async createQuotation({ additionalContext = {} } = {}) {
        const saved = await this._saveIfNeeded();
        if (!saved) {
            return;
        }

        if (!additionalContext.default_sale_order_template_id) {
            // If the user doesn't specify a template, we remove the previous one from the context
            additionalContext.default_sale_order_template_id = false;
        }

        if (this.isFormView) {
            await this.props.record.model.load({
                resId: false,
                mode: "edit",
                context: additionalContext,
            });
            return;
        }

        await this.action.doAction(this.action.currentAction, {
            viewType: "form",
            additionalContext,
        });
    }

    onEditClick(templateId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "sale.order.template",
            res_id: templateId,
            views: [[false, "form"]],
        });
    }

    async onDeleteClick(templateId) {
        this.dialogService.add(ConfirmationDialog, {
            body: deleteConfirmationMessage,
            confirm: async () => {
                await this.orm.unlink("sale.order.template", [templateId]);
                this.action.doAction("soft_reload");
            },
            cancel: () => {},
        });
    }

}
