import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { FormController } from "@web/views/form/form_controller";
import { formView } from "@web/views/form/form_view";

export class ProductExpenseFormController extends FormController {
    setup() {
        super.setup();
        this.dialog = useService("dialog");
    }

    async save(params) {
        await this.model._askChanges();
        const { id, standard_price, product_variant_id } = this.model.root.data;
        const productId = product_variant_id?.id || id;
        if (!productId) {
            return super.save(params);
        }

        const warning = await this.orm.call(
            "product.product",
            "get_standard_price_update_warning",
            [productId, standard_price],
        );

        if (warning) {
            return this.dialog.add(ConfirmationDialog, {
                body: warning,
                confirmLabel: _t("Update cost"),
                confirm: () => super.save(params),
                cancelLabel: _t("Discard"),
                cancel: () => {},
            });
        }

        return super.save(params);
    }
}

export const ProductExpenseFormView = {
    ...formView,
    Controller: ProductExpenseFormController,
};

registry.category("views").add("hr_expense_product_form", ProductExpenseFormView);
