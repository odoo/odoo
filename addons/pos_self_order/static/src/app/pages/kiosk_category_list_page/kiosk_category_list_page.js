import { Component, onWillStart } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/services/self_order_service";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { CancelPopup } from "@pos_self_order/app/components/cancel_popup/cancel_popup";

export class KioskCategoryListPage extends Component {
    static template = "pos_self_order.KioskCategoryListPage";
    static props = {};

    setup() {
        this.selfOrder = useSelfOrder();
        this.router = useService("router");
        this.dialog = useService("dialog");

        onWillStart(() => {
            this.selfOrder.computeAvailableCategories();
        });
    }

    shouldGoBack() {
        const order = this.selfOrder.currentOrder;
        return Object.keys(order.changes).length === 0 || order.lines.length === 0;
    }

    onClickBack() {
        if (!this.shouldGoBack()) {
            this.dialog.add(CancelPopup, {
                title: _t("Cancel order"),
                confirm: () => {
                    this.selfOrder.cancelOrder();
                    this.router.navigate("default");
                },
            });
            return;
        }

        if (this.selfOrder.hasPresets()) {
            this.router.navigate("location");
        } else {
            this.router.navigate("default");
        }
    }

    selectCategory(category) {
        this.selfOrder.currentCategory = category;
        this.router.navigate("product_list");
    }

    get categories() {
        return this.selfOrder.availableCategories.filter((c) => !c.parent_id);
    }
}
