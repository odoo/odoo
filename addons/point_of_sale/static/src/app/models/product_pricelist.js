import { registry } from "@web/core/registry";
import { Base } from "./related_models";

export class ProductPricelist extends Base {
    static pythonModel = "product.pricelist";

    setup() {
        super.setup(...arguments);

        this.uiState = {
            generalRulesByCateg: {},
            generalRules: {},
        };

        // General rules can be computed only on starting since they
        // are loaded by default, if a new pricelist is created
        // after the POS is started, it will be computed during the setup
        this.computeGeneralRulesByCateg();
    }

    getGeneralRulesByCategories(categoryIds) {
        const rules = {};

        for (const id of categoryIds) {
            if (this.uiState.generalRulesByCateg[id]) {
                Object.assign(rules, this.uiState.generalRulesByCateg[id]);
            }
        }

        Object.assign(rules, this.uiState.generalRules);
        return Object.values(rules);
    }

    computeGeneralRulesByCateg() {
        for (const index in this.item_ids) {
            const item = this.item_ids[index];
            if (item.product_id || item.product_tmpl_id) {
                continue;
            }

            if (item.categ_id) {
                if (!this.uiState.generalRulesByCateg[item.categ_id.id]) {
                    this.uiState.generalRulesByCateg[item.categ_id.id] = {};
                }

                this.uiState.generalRulesByCateg[item.categ_id.id][index] = item;
                continue;
            }

            this.uiState.generalRules[index] = item;
        }
    }
}

registry.category("pos_available_models").add(ProductPricelist.pythonModel, ProductPricelist);
