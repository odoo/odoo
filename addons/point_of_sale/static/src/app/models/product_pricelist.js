import { registry } from "@web/core/registry";
import { Base } from "./related_models";

export class ProductPricelist extends Base {
    static pythonModel = "product.pricelist";

    setup() {
        super.setup(...arguments);

        this.uiState = {
            generalRulesIdsByCateg: {},
            generalRulesIds: {},
            rulesByProductId: {},
            rulesByTmplId: {},
        };

        // General rules can be computed only on starting since they
        // are loaded by default, if a new pricelist is created
        // after the POS is started, it will be computed during the setup
        this.computeRuleIndexes();
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

    getRulesByProductId(productId) {
        return this.uiState.rulesByProductId[productId] || [];
    }

    getRulesByTmplId(tmplId) {
        return this.uiState.rulesByTmplId[tmplId] || [];
    }

    computeRuleIndexes() {
        for (let i = 0; i < this.item_ids.length; i++) {
            const item = this.item_ids[i];

            // Index by product_id (variant rules)
            if (item.product_id) {
                const prodId = item.product_id.id;
                if (!this.uiState.rulesByProductId[prodId]) {
                    this.uiState.rulesByProductId[prodId] = [];
                }
                this.uiState.rulesByProductId[prodId].push(item);
                continue;
            }

            // Index by product_tmpl_id (template rules)
            if (item.product_tmpl_id) {
                const tmplId = item.product_tmpl_id.id;
                if (!this.uiState.rulesByTmplId[tmplId]) {
                    this.uiState.rulesByTmplId[tmplId] = [];
                }
                this.uiState.rulesByTmplId[tmplId].push(item);
                continue;
            }

            if (item.categ_id) {
                if (!this.uiState.generalRulesIdsByCateg[item.categ_id.id]) {
                    this.uiState.generalRulesIdsByCateg[item.categ_id.id] = {};
                }

                this.uiState.generalRulesIdsByCateg[item.categ_id.id][i] = item.id;
                continue;
            }

            this.uiState.generalRulesIds[i] = item.id;
        }
    }
}

registry.category("pos_available_models").add(ProductPricelist.pythonModel, ProductPricelist);
