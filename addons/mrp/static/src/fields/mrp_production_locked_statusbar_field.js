import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import {
    stockPickingLockedStatusBarField,
    StockPickingLockedStatusBarField,
} from "@stock/fields/stock_picking_locked_statusbar_field";

export class MrpProductionLockedStatusBarField extends StockPickingLockedStatusBarField {
    static template = "mrp.ProductionLockedStatusBarField";
}

export const mrpProductionLockedStatusBarField = {
    ...stockPickingLockedStatusBarField,
    component: MrpProductionLockedStatusBarField,
    displayName: _t("Status bar with lock/unlock indicator for MO"),
};

registry
    .category("fields")
    .add("mrp_production_locked_statusbar", mrpProductionLockedStatusBarField);
