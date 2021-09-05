odoo.define('point_of_sale.OrderManagementControlPanel', function (require) {
    'use strict';

    const { useContext } = owl.hooks;
    const { useAutofocus, useListener } = require('web.custom_hooks');
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const OrderFetcher = require('point_of_sale.OrderFetcher');
    const contexts = require('point_of_sale.PosContext');

    // NOTE: These are constants so that they are only instantiated once
    // and they can be used efficiently by the OrderManagementControlPanel.
    const VALID_SEARCH_TAGS = new Set(['date', 'customer', 'client', 'name', 'order']);
    const FIELD_MAP = {
        date: 'date_order',
        customer: 'partner_id.display_name',
        client: 'partner_id.display_name',
        name: 'pos_reference',
        order: 'pos_reference',
    };
    const SEARCH_FIELDS = ['pos_reference', 'partner_id.display_name', 'date_order'];

    function getDomainForSingleCondition(fields, toSearch) {
        const orSymbols = Array(fields.length - 1).fill('|');
        return orSymbols.concat(fields.map((field) => [field, 'ilike', `%${toSearch}%`]));
    }

    /**
     * @emits close-screen
     * @emits prev-page
     * @emits next-page
     * @emits search
     */
    class OrderManagementControlPanel extends PosComponent {
        constructor() {
            super(...arguments);
            // We are using context because we want the `searchString` to be alive
            // even if this component is destroyed (unmounted).
            this.orderManagementContext = useContext(contexts.orderManagement);
            useListener('clear-search', this._onClearSearch);
            useAutofocus({ selector: 'input' });
        }
        onInputKeydown(event) {
            if (event.key === 'Enter') {
                this.trigger('search', this._computeDomain());
            }
        }
        get showPageControls() {
            return OrderFetcher.lastPage > 1;
        }
        get pageNumber() {
            const currentPage = OrderFetcher.currentPage;
            const lastPage = OrderFetcher.lastPage;
            return isNaN(lastPage) ? '' : `(${currentPage}/${lastPage})`;
        }
        get validSearchTags() {
            return VALID_SEARCH_TAGS;
        }
        get fieldMap() {
            return FIELD_MAP;
        }
        get searchFields() {
            return SEARCH_FIELDS;
        }
        /**
         * E.g. 1
         * ```
         *   searchString = 'Customer 1'
         *   result = [
         *      '|',
         *      '|',
         *      ['pos_reference', 'ilike', '%Customer 1%'],
         *      ['partner_id.display_name', 'ilike', '%Customer 1%'],
         *      ['date_order', 'ilike', '%Customer 1%']
         *   ]
         * ```
         *
         * E.g. 2
         * ```
         *   searchString = 'date: 2020-05'
         *   result = [
         *      ['date_order', 'ilike', '%2020-05%']
         *   ]
         * ```
         *
         * E.g. 3
         * ```
         *   searchString = 'customer: Steward, date: 2020-05-01'
         *   result = [
         *      ['partner_id.display_name', 'ilike', '%Steward%'],
         *      ['date_order', 'ilike', '%2020-05-01%']
         *   ]
         * ```
         */
        _computeDomain() {
            const input = this.orderManagementContext.searchString.trim();
            if (!input) return;

            const searchConditions = this.orderManagementContext.searchString.split(/[,&]\s*/);
            if (searchConditions.length === 1) {
                let cond = searchConditions[0].split(/:\s*/);
                if (cond.length === 1) {
                    return getDomainForSingleCondition(this.searchFields, cond[0]);
                }
            }
            const domain = [];
            for (let cond of searchConditions) {
                let [tag, value] = cond.split(/:\s*/);
                if (!this.validSearchTags.has(tag)) continue;
                domain.push([this.fieldMap[tag], 'ilike', `%${value}%`]);
            }
            return domain;
        }
        _onClearSearch() {
            this.orderManagementContext.searchString = '';
            this.onInputKeydown({ key: 'Enter' });
        }
    }
    OrderManagementControlPanel.template = 'OrderManagementControlPanel';

    Registries.Component.add(OrderManagementControlPanel);

    return OrderManagementControlPanel;
});
