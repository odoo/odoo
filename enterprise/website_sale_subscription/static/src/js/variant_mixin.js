/** @odoo-module **/

import VariantMixin from "@website_sale/js/sale_variant_mixin";
import { renderToElement } from "@web/core/utils/render";


/**
 * Update the renting text when the combination change.
 *
 * @param {Event} ev
 * @param {$.Element} $parent
 * @param {object} combination
 */
VariantMixin._onChangeCombinationSubscription = function (ev, $parent, combination) {
    if (!this.isWebsite || !combination.is_subscription) {
        return;
    }
    const parent = $parent.get(0);
    const unit = parent.querySelector(".o_subscription_unit");
    const price = parent.querySelector(".o_subscription_price") || parent.querySelector(".product_price h5");
    const pricingSelect =
        parent.querySelector(".js_main_product h5:has(.o_subscription_price)") ||
        parent.querySelector(".js_main_product select.plan_select");
    const pricingTable = document.querySelector("#oe_wsale_subscription_pricing_table");
    const addToCartButton = document.querySelector('#add_to_cart');
    if (addToCartButton) {
        addToCartButton.dataset.subscriptionPlanId = combination.pricings.length > 0 ? combination.subscription_default_pricing_plan_id : '';
    }
    if (unit) {
        unit.textContent = combination.temporal_unit_display;
    }
    if (price) {
        price.textContent = combination.subscription_default_pricing_price;
    }
    if (pricingSelect) {
        combination.formated_compared_price = pricingSelect.querySelector("del")?.textContent
        pricingSelect.replaceWith(
            renderToElement("website_sale_subscription.SubscriptionPricingSelect", {
                combination_info: combination,
            })
        );

        // only restore user input if relevant:
        // Present in the new combination data.
        // Set the value in the old select to the new
        // rendered select.
        if (combination.pricings.find(p => p.plan_id === parseInt(pricingSelect.value))) {
            const newPricingSelect = parent.querySelector(".js_main_product h5:has(.o_subscription_price)") ||
                parent.querySelector(".js_main_product select.plan_select");
            newPricingSelect.value = pricingSelect.value;
        }
    } else {
        // we dont find the element in the dom which means there was no pricings in the previous combination so there is no `select` or `h5` elements to replace then we append one.
        const nodeToAppend = parent.querySelector(".js_main_product div div");
        nodeToAppend.append(
            renderToElement("website_sale_subscription.SubscriptionPricingSelect", {
                combination_info: combination,
            })
        );
    }
    if (pricingTable) {
        pricingTable.replaceWith(
            renderToElement("website_sale_subscription.SubscriptionPricingTable", {
                combination_info: combination,
            })
        );
    } else {
        // we dont find the element in the dom which means there was no pricings in the previous combination so there is no `table` elements to replace then we append one.
        const nodeToAppend = document.querySelector("#product_details form");
        nodeToAppend.after(
            renderToElement("website_sale_subscription.SubscriptionPricingTable", {
                combination_info: combination,
            })
        );
    }
};

const oldGetOptionalCombinationInfoParam = VariantMixin._getOptionalCombinationInfoParam;
/**
 * Add the selected plan to the optional combination info parameters.
 *
 * @param {$.Element} $product
 */
VariantMixin._getOptionalCombinationInfoParam = function ($product) {
    const result = oldGetOptionalCombinationInfoParam.apply(this, arguments);
    Object.assign(result, {
        'plan_id': $product?.find('.product_price .plan_select').val()
    });

    return result;
};

export default VariantMixin;
