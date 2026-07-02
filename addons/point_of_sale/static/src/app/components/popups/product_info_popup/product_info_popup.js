import { useLayoutEffect } from "@web/owl2/utils";
import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { Component, proxy } from "@odoo/owl";
import { SnoozeDialog } from "./snooze_dialog/snooze_dialog";

export class ProductInfoPopup extends Component {
    static template = "point_of_sale.ProductInfoPopup";
    static components = { Dialog, SnoozeDialog };
    static props = ["info", "productTemplate", "close"];

    setup() {
        this.pos = usePos();
        this.ui = useService("ui");
        this.dialog = useService("dialog");
        this.state = proxy({
            countdown: "",
            activeSnooze: this.pos.getActiveSnooze("product", {
                product: this.props.productTemplate,
            }),
        });

        useLayoutEffect(
            () => {
                if (!this.state.activeSnooze) {
                    return;
                }
                this.updateSnoozeCountdown();
                const interval = setInterval(() => this.updateSnoozeCountdown(), 1000);
                return () => {
                    clearInterval(interval);
                };
            },
            () => [this.state.activeSnooze]
        );
    }
    updateSnoozeCountdown() {
        [this.state.countdown, this.state.activeSnooze] = this.pos.getSnoozeCountdown(
            this.state.activeSnooze
        );
        if (!this.ui.isSmall) {
            this.state.countdown = _t("%s left", this.state.countdown);
        }
    }
    searchProduct(productName) {
        this.pos.setSelectedCategory(0);
        this.pos.searchProductWord = productName;
        this.props.close();
    }
    _hasMarginsCostsAccessRights() {
        if (!this.pos.config.is_margins_costs_accessible_to_every_user) {
            return false;
        }
        return ["manager", "cashier"].includes(this.pos.getCashier()._role);
    }
    editProduct() {
        this.pos.editProduct(this.props.productTemplate);
        this.props.close();
    }
    get allowProductEdition() {
        return true; // Overrided in pos_hr
    }
    toggleFavorite() {
        this.pos.data.write("product.template", [this.props.productTemplate.id], {
            is_favorite: !this.props.productTemplate.is_favorite,
        });
    }
    get vatLabel() {
        return _t("Tax:");
    }
    get totalVatLabel() {
        return _t("Total Tax:");
    }
    openSnoozeDialog() {
        if (this.state.activeSnooze) {
            this.pos.unSnoozeItem(this.state.activeSnooze, () => {
                this.state.activeSnooze = undefined;
                this.state.countdown = "";
            });
            return;
        }
        this.pos.snoozeItem(
            "product",
            (record) => {
                this.state.activeSnooze = record;
            },
            { product_template_id: this.props.productTemplate.id }
        );
    }
}
