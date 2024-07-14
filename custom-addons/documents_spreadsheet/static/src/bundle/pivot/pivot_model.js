/** @odoo-module */

import { SpreadsheetPivotModel } from "@spreadsheet/pivot/pivot_model";
import { patch } from "@web/core/utils/patch";
import { Domain } from "@web/core/domain";

patch(SpreadsheetPivotModel.prototype, {
    setup() {
        super.setup(...arguments);
        /**
         * Contains the possible values for each group by of the pivot. This attribute is used *only* for templates,
         * so it's computed only in prepareForTemplateGeneration
         */
        this._fieldsValue = {};
    },

    /**
     * Get the possible values for the given groupBy
     * @param {string} groupBy
     * @returns {any[]}
     */
    getPossibleValuesForGroupBy(groupBy) {
        return this._fieldsValue[groupBy] || [];
    },

    /**
     * This method is used to compute the possible values for each group bys.
     * It should be run before using templates
     */
    async prepareForTemplateGeneration() {
        const colValues = [];
        const rowValues = [];

        function collectValues(tree, collector) {
            const group = tree.root;
            if (!tree.directSubTrees.size) {
                //It's a leaf, we can fill the cols
                collector.push([...group.values]);
            }
            [...tree.directSubTrees.values()].forEach((subTree) => {
                collectValues(subTree, collector);
            });
        }

        collectValues(this.data.colGroupTree, colValues);
        collectValues(this.data.rowGroupTree, rowValues);

        for (let i = 0; i < this.metaData.fullRowGroupBys.length; i++) {
            let vals = [
                ...new Set(rowValues.map((array) => array[i]).filter((val) => val !== undefined)),
            ];
            if (i !== 0) {
                vals = await this._orderValues(vals, this.metaData.fullRowGroupBys[i]);
            }
            this._fieldsValue[this.metaData.fullRowGroupBys[i]] = vals;
        }
        for (let i = 0; i < this.metaData.fullColGroupBys.length; i++) {
            let vals = [];
            if (i !== 0) {
                vals = await this._orderValues(vals, this.metaData.fullColGroupBys[i]);
            } else {
                vals = colValues.map((array) => array[i]).filter((val) => val !== undefined);
                vals = [...new Set(vals)];
            }
            this._fieldsValue[this.metaData.fullColGroupBys[i]] = vals;
        }
    },

    /**
     * Order the given values for the given groupBy. This is done by executing a
     * search_read
     */
    async _orderValues(values, groupBy) {
        const field = this.parseGroupField(groupBy).field;
        const model = this.metaData.resModel;
        const context = this.searchParams.context;
        const baseDomain = this.searchParams.domain;
        const requestField = field.relation ? "id" : field.name;
        const domain = Domain.and([
            field.relation ? [] : baseDomain,
            [[requestField, "in", values]],
        ]).toList();
        // orderby is omitted for relational fields on purpose to have the default order of the model
        const records = await this.orm.searchRead(
            field.relation ? field.relation : model,
            domain,
            [requestField],
            {
                order: field.relation ? undefined : `${field.name} ASC`,
                context: { ...context, active_test: false },
            }
        );
        return [...new Set(records.map((record) => record[requestField].toString()))];
    },
});
