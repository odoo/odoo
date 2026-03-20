import { registry } from "@web/core/registry";
import { Base } from "./related_models";

export class ProductPricelist extends Base {
    static pythonModel = "product.pricelist";

    setup() {
        super.setup(...arguments);

        this.uiState = {
            generalRulesIdsByCateg: {},
            generalRulesIds: {},
        };

        // General rules can be computed only on starting since they
        // are loaded by default, if a new pricelist is created
        // after the POS is started, it will be computed during the setup
        this.computeGeneralRulesByCateg();
    }

    getGeneralRulesIdsByCategories(categoryIds) {
        const rules = {};

        for (const id of categoryIds) {
            if (this.uiState.generalRulesIdsByCateg[id]) {
                Object.assign(rules, this.uiState.generalRulesIdsByCateg[id]);
            }
        }

        Object.assign(rules, this.uiState.generalRulesIds);
        return Object.values(rules);
    }

    computeGeneralRulesByCateg() {
        for (const idx in this.item_ids) {
            const index = parseInt(idx);
            const item = this.item_ids[index];
            if (item.product_id || item.product_tmpl_id) {
                continue;
            }

            if (item.categ_id) {
                if (!this.uiState.generalRulesIdsByCateg[item.categ_id.id]) {
                    this.uiState.generalRulesIdsByCateg[item.categ_id.id] = {};
                }

                this.uiState.generalRulesIdsByCateg[item.categ_id.id][index] = item.id;
                continue;
            }

            this.uiState.generalRulesIds[index] = item.id;
        }
    }
}

registry.category("pos_available_models").add(ProductPricelist.pythonModel, ProductPricelist);
