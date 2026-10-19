import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { statusBarField, StatusBarField } from "@web/views/fields/statusbar/statusbar_field";

export class StockPickingLockedStatusBarField extends StatusBarField {
    static template = "stock.PickingLockedStatusBarField";

    get isLocked() {
        return this.props.record.data.is_locked;
    }

    get currentItem() {
        return this.getAllItems().find((item) => item.isSelected);
    }
}

export const stockPickingLockedStatusBarField = {
    ...statusBarField,
    component: StockPickingLockedStatusBarField,
    displayName: _t("Status bar with lock/unlock indicator for Pickings"),
    supportedTypes: ["selection"],
    additionalClasses: ["o_field_statusbar"],
};

registry.category("fields").add("stock_picking_locked_statusbar", stockPickingLockedStatusBarField);
