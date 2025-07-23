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
        const { id: productId, standard_price } = this.model.root.data;
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
