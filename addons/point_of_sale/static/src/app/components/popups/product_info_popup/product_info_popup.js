import { Dialog } from "@web/core/dialog/dialog";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { Component } from "@odoo/owl";
import { ProductInfoBanner } from "@point_of_sale/app/components/product_info_banner/product_info_banner";

export class ProductInfoPopup extends Component {
    static template = "point_of_sale.ProductInfoPopup";
    static components = { Dialog, ProductInfoBanner };
    static props = ["info", "productTemplate", "close"];

    setup() {
        this.pos = usePos();
    }
    searchProduct(productName) {
        this.pos.setSelectedCategory(0);
        this.pos.searchProductWord = productName;
        this.props.close();
    }
    _hasMarginsCostsAccessRights() {
        const isAccessibleToEveryUser = this.pos.config.is_margins_costs_accessible_to_every_user;
        const isCashierManager = this.pos.getCashier().role === "manager";
        return isAccessibleToEveryUser || isCashierManager;
    }
    editProduct() {
        this.pos.editProduct(this.props.product);
        this.props.close();
    }
<<<<<<< master:addons/point_of_sale/static/src/app/components/popups/product_info_popup/product_info_popup.js
||||||| 204fbd00019c655e4becbef66ab235229166a468:addons/point_of_sale/static/src/app/screens/product_screen/product_info_popup/product_info_popup.js
    get isVariant() {
        return (
            this.pos.models["product.product"].filter(
                (p) => p.raw.product_tmpl_id === this.props.product.raw.product_tmpl_id
            ).length > 1
        );
    }
=======
    get isVariant() {
        return this.pos.isProductVariant(this.props.product);
    }
>>>>>>> a592f2433588a00c3d06ecdcd0749933df8b4db7:addons/point_of_sale/static/src/app/screens/product_screen/product_info_popup/product_info_popup.js
    get allowProductEdition() {
        return true; // Overrided in pos_hr
    }
}
