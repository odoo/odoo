/** @odoo-module **/

import { qweb, _t } from 'web.core';
import fieldRegistry from 'web.field_registry';
import { FieldSelection } from 'web.relational_fields';


export const HierarchySelection = FieldSelection.extend({

    init: function () {
        this._super.apply(this, arguments);
        this.hierarchyGroups = [
            {name: _t('Balance Sheet')},
            {name: _t('Assets'), children: this.values.filter(x => x[0] && x[0].startsWith('asset'))},
            {name: _t('Liabilities'), children: this.values.filter(x => x[0] && x[0].startsWith('liability'))},
            {name: _t('Equity'), children: this.values.filter(x => x[0] && x[0].startsWith('equity'))},
            {name: _t('Profit & Loss')},
            {name: _t('Income'), children: this.values.filter(x => x[0] && x[0].startsWith('income'))},
            {name: _t('Expense'), children: this.values.filter(x => x[0] && x[0].startsWith('expense'))},
            {name: _t('Other'), children: this.values.filter(x => x[0] && x[0] == 'off_balance')},
        ];
    },

    _renderEdit: function () {
        this.$el.empty();
        this.$el.append(qweb.render('accountTypeSelection', {widget: this}));
        this.$el.val(JSON.stringify(this._getRawValue()));
    }
});

fieldRegistry.add("account_type_selection", HierarchySelection);
