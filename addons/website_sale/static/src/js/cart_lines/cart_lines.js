import { Component, onWillStart, providePlugins, t, useProps } from "@odoo/owl";
import { CartLine } from "./cart_line/cart_line";
import { CartAccessories } from "./cart_accessories/cart_accessories";
import { useService } from "@web/core/utils/hooks";
import { CartPlugin } from "@website_sale/js/cart_plugin";

export class CartLines extends Component {
    static template = "website_sale.CartLines";
    static components = { CartLine, CartAccessories };
    props = useProps({ templateData: t.object() });

    setup() {
        providePlugins([CartPlugin]);
        this.cartService = useService("cart");
        onWillStart(async () => {
            await this.cartService.loadCart({ withHistory: true });
        });
    }

    get data() {
        return this.cartService.state.lines;
    }

    get lines() {
        return this.data.cart_lines ?? [];
    }

    get cartLinesProps() {
        return {
            templateData: this.props.templateData,
        };
    }

    get cartAccessoriesProps() {
        return {
            templateData: this.props.templateData,
            accessories: this.data.accessories,
        };
    }
}
