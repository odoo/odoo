import { registry } from "@web/core/registry";
import { Base } from "./related_models";

export class ProductPricelist extends Base {
    static pythonModel = "product.pricelist";

    setup() {
        super.setup(...arguments);

        this.rulesByProductId = {};
        this.rulesByTmplId = {};
        this.uiState = {
            generalRulesIdsByCateg: {},
            generalRulesIds: {},
        };

        // General rules can be computed only on starting since they
        // are loaded by default, if a new pricelist is created
        // after the POS is started, it will be computed during the setup
        this.computeRuleIndexes();
    }

    getCategoryRulesIds(categoryIds) {
        const rules = {};

        for (const id of categoryIds) {
            if (this.uiState.generalRulesIdsByCateg[id]) {
                Object.assign(rules, this.uiState.generalRulesIdsByCateg[id]);
            }
        }

        return Object.values(rules);
    }

    getGlobalRulesIds() {
        return Object.values(this.uiState.generalRulesIds);
    }

    getRulesByProductId(productId) {
        return this.rulesByProductId[productId] || [];
    }

    getRulesByTmplId(tmplId) {
        return this.rulesByTmplId[tmplId] || [];
    }

    computeRuleIndexes() {
        this.rulesByProductId = {};
        this.rulesByTmplId = {};
        this.uiState.generalRulesIdsByCateg = {};
        this.uiState.generalRulesIds = {};

        for (let i = 0; i < this.item_ids.length; i++) {
            const item = this.item_ids[i];

            // Index by product_id (variant rules)
            if (item.product_id) {
                const prodId = item.product_id.id;
                if (!this.rulesByProductId[prodId]) {
                    this.rulesByProductId[prodId] = [];
                }
                this.rulesByProductId[prodId].push(item);
                continue;
            }

            // Index by product_tmpl_id (template rules)
            if (item.product_tmpl_id) {
                const tmplId = item.product_tmpl_id.id;
                if (!this.rulesByTmplId[tmplId]) {
                    this.rulesByTmplId[tmplId] = [];
                }
                this.rulesByTmplId[tmplId].push(item);
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

    findBestRule(rules, quantity) {
        let bestRule = null;
        for (const rule of rules) {
            if (!rule.min_quantity || rule.min_quantity <= quantity) {
                if (!bestRule || rule.min_quantity > bestRule.min_quantity) {
                    bestRule = rule;
                }
            }
        }
        return bestRule;
    }
}

registry.category("pos_available_models").add(ProductPricelist.pythonModel, ProductPricelist);
