import { Component, onWillStart, useProps, proxy, t } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog, deleteConfirmationMessage } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { user } from "@web/core/user";
import { localization } from "@web/core/l10n/localization";

const isRTL = () => localization.direction === "rtl";
const isRowAction = (item) => Boolean(item?.el.closest(".o_template_icon_group"));
const rowsOf = (navigator) => navigator.items.filter((item) => !isRowAction(item));

/** Activates the next row in the `step` direction, skipping the rows' actions. */
function moveToRow(navigator, step) {
    const move = step > 0 ? () => navigator.next() : () => navigator.previous();
    for (let i = 0; i < navigator.items.length; i++) {
        move();
        if (!isRowAction(navigator.activeItem)) {
            return;
        }
    }
}

/** Steps into the actions of the active row, and back out of them. */
function moveWithinRow(navigator, step) {
    const { items, activeItemIndex } = navigator;
    const target = items[activeItemIndex + step];
    if (activeItemIndex < 0 || !target) {
        return;
    }
    // Stepping in has to land on an action, stepping out has to start from one,
    // which is what keeps a row from reaching its neighbour's actions.
    if (isRowAction(step > 0 ? target : items[activeItemIndex])) {
        target.setActive();
    }
}

// The hotkeys are given as objects so that deepMerge keeps the flags the
// framework sets on them.
const navigationOptions = {
    // false: the default would target each row's first nested <button> (the edit
    // icon), so Enter would open the template instead of using it.
    shouldFocusChildInput: false,
    hotkeys: {
        // Up and down walk the rows, left and right reach the actions of a row.
        // Tab is left alone, so it still steps through every item.
        arrowdown: { callback: (navigator) => moveToRow(navigator, 1) },
        arrowup: { callback: (navigator) => moveToRow(navigator, -1) },
        arrowright: { callback: (navigator) => moveWithinRow(navigator, isRTL() ? -1 : 1) },
        arrowleft: { callback: (navigator) => moveWithinRow(navigator, isRTL() ? 1 : -1) },
        // Rows again, otherwise End would land on a row's last action.
        home: (navigator) => rowsOf(navigator)[0]?.setActive(),
        end: (navigator) => rowsOf(navigator).at(-1)?.setActive(),
        // Rebound because the rows are <span>, not <button>.
        space: (navigator) => navigator.activeItem?.select(),
    },
};

export class SaleTemplateDropdown extends Component {
    static template = "sale_management.SaleTemplateDropdown";
    static components = {
        Dropdown,
        DropdownItem,
    };

    props = useProps({
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
        this.navigationOptions = navigationOptions;
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
