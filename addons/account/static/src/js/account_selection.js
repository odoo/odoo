odoo.define('account.hierarchy.selection', function (require) {
"use strict";

    const core = require('web.core');
    const relational_fields = require('web.relational_fields');
    const _t = core._t;
    const registry = require('web.field_registry');
    const FieldSelection = relational_fields.FieldSelection;
    const qweb = core.qweb;

    const ACCOUNT_TYPE_HIERARCHY = [
        [_t("Equity"),                      'account.data_account_type_equity', [
            [_t("Current Year Earnings"),       'account.data_unaffected_earnings'],
        ]],
        [_t("Assets"),                      null, [
            [_t("Current Assets"),              'account.data_account_type_current_assets', [
                [_t("Bank and Cash"),               'account.data_account_type_liquidity'],
                [_t("Prepayments"),                 'account.data_account_type_prepayments'],
                [_t("Receivable"),                  'account.data_account_type_receivable'],
            ]],
            [_t("Non Current Assets"),          'account.data_account_type_non_current_assets', [
                [_t("Fixed Assets"),                'account.data_account_type_fixed_assets'],
            ]],
        ]],
        [_t("Liabilities"),                 null, [
            [_t("Payable"),                     'account.data_account_type_payable'],
            [_t("Current Liabilities"),         'account.data_account_type_current_liabilities'],
            [_t("Non-Current Liabilities"),     'account.data_account_type_non_current_liabilities'],
            [_t("Credit Card"),                 'account.data_account_type_credit_card'],
        ]],
        [_t("Income"),                      null, [
            [_t("Revenue"),                     'account.data_account_type_revenue'],
            [_t("Other Income"),                'account.data_account_type_other_income'],
        ]],
        [_t("Expense"),                     null, [
            [_t("Expenses"),                    'account.data_account_type_expenses'],
            [_t("Depreciation"),                'account.data_account_type_depreciation'],
            [_t("Cost of Revenue"),             'account.data_account_type_direct_costs'],
        ]],
        [_t("Off Balance"),                 'account.data_account_off_sheet'],
    ];

    var HierarchySelection = FieldSelection.extend({

        /**
         * Build the multi-level account type hierarchy based on ACCOUNT_TYPE_HIERARCHY as a "select" widget.
         * @private
         * @param {jQuery} element:                 parent jquery element on which append the newly created <option/>.
         * @param {Array} hierarchyNode:            A node inside ACCOUNT_TYPE_HIERARCHY as a list.
         * @param {Integer} level:                  The level inside the travelled hierarchy.
         */
        _renderAccountTypeHierarchy: function(element, hierarchyNode, level){
            var self = this;

            var text = hierarchyNode[0];
            var xmlId = hierarchyNode[1];
            var childrenNodes = hierarchyNode[2] || [];

            var label = $('<div/>').html('&nbsp;'.repeat(6 * level) + text).text();

            // Sub-Tree of options.
            element.append($('<option/>', {
                text: label,
                disabled: xmlId == null,
                value: xmlId == null ? null : JSON.stringify(self.account_types_mapping[xmlId][0]),
            }));
            _.each(childrenNodes, function(childNode){
                self._renderAccountTypeHierarchy(element, childNode, level + 1);
            });
        },

        /**
         * @Override
         * Shadow completely the rendering to display the account type hierarchy with multiple levels.
         */
        _renderEdit: function () {
            var self = this;

            var promise = Promise.resolve();
            if(!self.account_types_mapping){
                promise = this._rpc({
                    model: 'account.account.type',
                    method: 'js_fetch_account_types_with_xml_ids',
                }).then(function(account_types_mapping){
                    self.values = Object.values(account_types_mapping);
                    self.account_types_mapping = account_types_mapping;
                });
            }

            Promise.resolve(promise).then(function() {
                // Display the hierarchy of codes.
                self.$el.empty();
                _.each(ACCOUNT_TYPE_HIERARCHY, function(hierarchyNode){
                    self._renderAccountTypeHierarchy(self.$el, hierarchyNode, 0);
                });

                // Format displayed value.
                self.$el.val(JSON.stringify(self._getRawValue()));
            });
        },

    });
    registry.add("account_hierarchy_selection", HierarchySelection);
});
