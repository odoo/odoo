import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { Component, useProps, t } from "@odoo/owl";
import { SnoozeDialog } from "./snooze_dialog/snooze_dialog";
import { ProductTemplate } from "@point_of_sale/app/models/product_template";

export class ProductInfoPopup extends Component {
    static template = "point_of_sale.ProductInfoPopup";
    static components = { Dialog, SnoozeDialog };
    props = useProps({
        info: t.object(),
        productTemplate: t.instanceOf(ProductTemplate),
        close: t.function(),
    });

    setup() {
        this.pos = usePos();
        this.ui = useService("ui");
        this.dialog = useService("dialog");
    }

    get activeSnooze() {
        return this.pos.getActiveSnooze("product", {
            product: this.props.productTemplate,
        });
    }
    get snoozeCountdown() {
        if (!this.activeSnooze) {
            return "";
        }

        const [countdown] = this.pos.getSnoozeCountdown(this.activeSnooze);
        if (!countdown) {
            return "";
        }
        if (!this.activeSnooze.end_time) {
            return countdown;
        }
        return this.ui.isSmall ? countdown : _t("%s left", countdown);
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
        return ["manager", "cashier"].includes(this.pos.accessRight.loggedCashier._role);
    }
    editProduct() {
        this.pos.editProduct(this.props.productTemplate);
        this.props.close();
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
        if (this.activeSnooze) {
            this.pos.unSnoozeItem(this.activeSnooze);
            return;
        }
        this.pos.snoozeItem("product", undefined, {
            product_template_id: this.props.productTemplate.id,
        });
    }
    get taxDetails() {
        return this.props.info.productTaxDetails;
    }
}
