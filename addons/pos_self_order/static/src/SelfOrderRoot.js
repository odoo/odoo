/** @odoo-module */
import { Component, whenReady, App, useState, useSubEnv } from "@odoo/owl";
import { makeEnv, startServices } from "@web/env";
import { setLoadXmlDefaultApp, templates } from "@web/core/assets";
import { _t } from "@web/core/l10n/translation";
import { LandingPage } from "@pos_self_order/LandingPage/LandingPage";
import { NavBar } from "@pos_self_order/NavBar/NavBar";
import { ProductMainView } from "@pos_self_order/ProductMainView/ProductMainView";
import { ProductList } from "@pos_self_order/ProductList/ProductList";
import { useSelfOrder } from "@pos_self_order/SelfOrderService";
import { Router } from "@pos_self_order/router";
import { groupBy } from "@web/core/utils/arrays";

class SelfOrderRoot extends Component {
    static template = "pos_self_order.SelfOrderRoot";
    static components = {
        LandingPage,
        ProductMainView,
        NavBar,
        ProductList,
        Router,
    };
    /*
    This is the Root Component of the SelfOrder App
    Most of the business logic is done here
    The app has the folowing screens:
    0. LandingPage  -- the main screen of the app
                    -- it has a button that redirects to the menu
    1. ProductList -- the screen that shows the list of products ( the menu )
    2. ProductMainView  -- the screen that shows the details of a product ( the product page )
    */
    setup() {
        this.selfOrder = useSelfOrder();
        this.state = useState({
            currentProduct: 0,
        });
        useSubEnv({ state: this.state });
        this.selfOrder.products = this.selfOrder.products.map(
            ({
                id,
                pos_categ_id,
                price_info,
                display_name,
                description_sale,
                attribute_line_ids,
                ...rest
            }) => ({
                product_id: id,
                list_price: this.selfOrder.show_prices_with_tax_included
                    ? price_info["price_with_tax"]
                    : price_info["price_without_tax"],
                tag: pos_categ_id ? pos_categ_id[1].split(" / ").at(-1) : "Other",
                // the display name is like '[FURN_7888] Desk Stand with Screen' so we remove the [FURN_7888] part
                name: display_name.replace(/^\[.*]/g, ""),
                // we add the attributes to the products
                attributes: getProductAttributes(
                    attribute_line_ids,
                    this.selfOrder.attributes_by_ptal_id
                ),
                description_sale: description_sale ? description_sale : "",
                ...rest,
            })
        );
        // we create a set with all the tags that are present in the menu
        this.selfOrder.tagList = new Set(this.selfOrder.products.map((product) => product.tag));
        this.selfOrder.productListGroupedByTag = groupBy(this.selfOrder.products, "tag");
    }
}
export function getProductAttributes(attribute_line_ids, attributes_by_ptal_id) {
    return attribute_line_ids.some((id) => id in attributes_by_ptal_id)
        ? attribute_line_ids
              .map((id) => attributes_by_ptal_id[id])
              .filter((attr) => attr !== undefined)
        : [];
}

export async function createPublicRoot() {
    await whenReady();
    const env = makeEnv();
    await startServices(env);
    const app = new App(SelfOrderRoot, {
        templates,
        env: env,
        dev: env.debug,
        translateFn: _t,
        translatableAttributes: ["data-tooltip"],
    });
    setLoadXmlDefaultApp(app);
    return app.mount(document.body);
}
createPublicRoot();
export default { SelfOrderRoot, createPublicRoot };
