import { registry } from "@web/core/registry";
import { Base } from "./related_models";

const { DateTime } = luxon;

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

        // Rules are added to uiState through addRuleIndex,
        // addRuleIndex is called by the product.pricelist.item when setup.
        this.rulesByProductId = {};
        this.rulesByTmplId = {};
        this.uiState.generalRulesIdsByCateg = {};
        this.uiState.generalRulesIds = {};
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

    addRuleIndex(item, index) {
        // Read the ids from the raw data: the targeted record may not be loaded in
        // the PoS, and a rule must not be treated as global just because its target
        // is missing.
        const { product_id, product_tmpl_id, categ_id } = item.raw;
        // Index by product_id (variant rules)
        if (product_id) {
            if (!this.rulesByProductId[product_id]) {
                this.rulesByProductId[product_id] = [];
            }
            this.rulesByProductId[product_id].push(item);
            return;
        }

        // Index by product_tmpl_id (template rules)
        if (product_tmpl_id) {
            if (!this.rulesByTmplId[product_tmpl_id]) {
                this.rulesByTmplId[product_tmpl_id] = [];
            }
            this.rulesByTmplId[product_tmpl_id].push(item);
            return;
        }

        if (categ_id) {
            if (!this.uiState.generalRulesIdsByCateg[categ_id]) {
                this.uiState.generalRulesIdsByCateg[categ_id] = {};
            }

            this.uiState.generalRulesIdsByCateg[categ_id][index] = item.id;
            return;
        }

        this.uiState.generalRulesIds[index] = item.id;
    }

    findBestRule(rules, quantity) {
        const now = DateTime.now();
        let bestRule = null;
        for (const rule of rules) {
            if (rule.date_start && rule.date_start > now) {
                continue;
            }
            if (rule.date_end && rule.date_end < now) {
                continue;
            }
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
