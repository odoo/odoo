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

        // General rules can be computed only on starting since they
        // are loaded by default, if a new pricelist is created
        // after the POS is started, it will be computed during the setup
        this.computeRuleIndexes();

        // Items loaded later (e.g. with new products) come without their pricelist
        const itemModel = this.models["product.pricelist.item"];
        if (!itemModel.indexesPricelistRules) {
            itemModel.indexesPricelistRules = true;
            itemModel.addEventListener("create", ({ ids }) => {
                const items = itemModel.readMany(ids);
                for (const pricelist of new Set(items.map((item) => item.pricelist_id))) {
                    pricelist?.indexNewRules(
                        items.filter((item) => item.pricelist_id === pricelist)
                    );
                }
            });
        }
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

        // The item_ids getter rebuilds the whole array on each access
        const items = this.item_ids;
        this.indexedItemIds = new Set(items.map((item) => item.id));
        for (let i = 0; i < items.length; i++) {
            const item = items[i];
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
                continue;
            }

            // Index by product_tmpl_id (template rules)
            if (product_tmpl_id) {
                if (!this.rulesByTmplId[product_tmpl_id]) {
                    this.rulesByTmplId[product_tmpl_id] = [];
                }
                this.rulesByTmplId[product_tmpl_id].push(item);
                continue;
            }

            if (categ_id) {
                if (!this.uiState.generalRulesIdsByCateg[categ_id]) {
                    this.uiState.generalRulesIdsByCateg[categ_id] = {};
                }

                this.uiState.generalRulesIdsByCateg[categ_id][i] = item.id;
                continue;
            }

            this.uiState.generalRulesIds[i] = item.id;
        }
    }

    indexNewRules(items) {
        items = items.filter((item) => !this.indexedItemIds.has(item.id));
        // Category and global rules are ordered by their position in item_ids
        if (items.some((item) => !item.raw.product_id && !item.raw.product_tmpl_id)) {
            this.computeRuleIndexes();
            return;
        }
        for (const item of items) {
            const { product_id, product_tmpl_id } = item.raw;
            const index = product_id ? this.rulesByProductId : this.rulesByTmplId;
            const key = product_id || product_tmpl_id;
            if (!index[key]) {
                index[key] = [];
            }
            index[key].push(item);
            this.indexedItemIds.add(item.id);
        }
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
