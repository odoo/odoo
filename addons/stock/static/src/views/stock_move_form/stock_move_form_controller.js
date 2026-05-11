import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { FormController } from "@web/views/form/form_controller";
import { formView } from "@web/views/form/form_view";

export class StockMoveFormController extends FormController {
    async save(params) {
        await this.model._askChanges();
        if (this._hasOverweightPackages()) {
            return this.dialogService.add(ConfirmationDialog, {
                title: _t("Package/s Too Heavy!"),
                body: _t(
                    "The weight of one or more packages is higher than the maximum weight authorized for their package type.\n" +
                        "Do you want to proceed anyway?"
                ),
                confirmLabel: _t("Save"),
                confirm: () => super.save(params),
                cancel: () => {},
            });
        }

        return super.save(params);
    }

    _hasOverweightPackages() {
        const packageData = {};
        const moveLines = this.model.root.data.move_line_ids.records;
        const productWeight = moveLines[0]?.data.product_weight || 0;

        if (!productWeight) {
            return false;
        }

        for (const { _values: old, data, dirty } of moveLines) {
            const packageId = data.result_package_id?.id;

            if (
                !packageId ||
                !dirty ||
                (old.result_package_id?.id === packageId &&
                    old.quantity_product_uom === data.quantity_product_uom) ||
                !data.package_max_weight
            ) {
                continue;
            }

            packageData[packageId] ??= {
                weight: data.package_weight || 0,
                maxWeight: data.package_max_weight || 0,
                baseWeight: data.package_base_weight || 0,
                qtyDelta: 0,
            };

            packageData[packageId].qtyDelta +=
                data.quantity_product_uom -
                (old.result_package_id?.id === packageId ? old.quantity_product_uom : 0);
        }

        return Object.values(packageData).some(
            ({ weight, qtyDelta, maxWeight, baseWeight }) =>
                weight + qtyDelta * productWeight > maxWeight + baseWeight
        );
    }
}

export const StockMoveFormView = {
    ...formView,
    Controller: StockMoveFormController,
};

registry.category("views").add("sm_form", StockMoveFormView);
