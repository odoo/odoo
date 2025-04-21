import { Countdown } from "@website/snippets/s_countdown/countdown";
import { registry } from "@web/core/registry";
import { rpc } from '@web/core/network/rpc';

export class ProductCountdown extends Countdown {
    getPublishedSearchDomain() {
        const searchDomain = [];
        const hideProductNames = this.el.dataset.hideProductNames;

        if (hideProductNames) {
            const nameFragments = hideProductNames.split(",").map(s => s.trim()).filter(Boolean);
            const orConditions = [];

            for (const fragment of nameFragments) {
                orConditions.push(
                    ["name", "ilike", fragment],
                    ["default_code", "=", fragment],
                    ["barcode", "=", fragment]
                );
            }

            // Combine into proper OR domain
            // If we have n conditions, we need (n-1) ORs
            if (orConditions.length > 1) {
                const domain = [];
                const ors = orConditions.length - 1;
                for (let i = 0; i < ors; i++) {
                    domain.push('|');
                }
                domain.push(...orConditions);
                searchDomain.push(...domain);
            } else {
                searchDomain.push(...orConditions);
            }
            return searchDomain;
        }
    }
    
    async set_prevent_zero_price_sale(){
        return rpc("/website_sale/product_configurator/set_prevent_zero_price_sale", {});
    }

    async hide_product(){
        await this.waitFor(rpc(
            "/website_sale/product_configurator/set_hide_products",
            Object.assign({
                "search_domain": this.getPublishedSearchDomain(),
            })
        ));
    }

    handleEndCountdownAction() {
        if (this.endAction === "prevent_sale_zero_priced_product"){
            this.set_prevent_zero_price_sale();
        } else if (this.endAction === "hide_product") {
            this.hide_product()
        } else{
            super.handleEndCountdownAction();
        }
    }
}

registry
    .category("public.interactions")
    .add("website.countdown", ProductCountdown, { force: true });
