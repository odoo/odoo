odoo.define('account.hierarchy.selection', function (require) {
"use strict";

    var core = require('web.core');
    var relational_fields = require('web.relational_fields');
    var _t = core._t;
    var registry = require('web.field_registry');


    var FieldSelection = relational_fields.FieldSelection;

    var qweb = core.qweb;

    var HierarchySelection = FieldSelection.extend({
        _renderEdit: function () {
            var self = this;
            var selectSuper = this._super;
            var prom = Promise.resolve();
            if (!self.hierarchy_groups) {
                prom = this._rpc({
                    model: 'account.account.type',
                    method: 'search_read',
                    kwargs: {
                        domain: self.record.context && self.record.context.account_type_domain || [],
                        fields: ['id', 'internal_group', 'display_name'],
                    },
                }).then(function(arg) {
                    self.values = _.map(arg, v => [v['id'], v['display_name']]);
                    var unique_groups = _.uniq(_.map(arg, v => v['internal_group']));
                    if (unique_groups.length > 1) {
                        var parent_lookup = {
                            'bs': {'name': _t('Balance Sheet'), 'index': 0},
                            'pl': {'name': _t('Profit & Loss'), 'index': 1},
                        }
                        var lookup = {
                            'asset': {'parent': 'bs', 'name': _t('Assets')},
                            'liability': {'parent': 'bs', 'name': _t('Liabilities')},
                            'equity': {'parent': 'bs', 'name': _t('Equity')},
                            'income': {'parent': 'pl', 'name': _t('Income')},
                            'expense': {'parent': 'pl', 'name': _t('Expense')},
                        }
                        var unique_parents = _.uniq(_.map(_.filter(unique_groups, u => u in lookup), g => lookup[g].parent));
                        self.hierarchy_groups = [];
                        _.each(unique_parents, parent_id => {
                            var parent = parent_lookup[parent_id];
                            self.hierarchy_groups.splice(parent.index, 0, {'name': parent.name, 'children': []});
                        });
                        var other_accounts_added = false;
                        _.each(unique_groups, g => {
                            if (g in lookup){
                                var rec = lookup[g];
                                self.hierarchy_groups[parent_lookup[rec.parent].index].children.push({
                                    'name': rec['name'],
                                    'ids': _.map(_.filter(arg, v => v['internal_group'] == g), v => v['id'])
                                });
                            } else if (!other_accounts_added){
                                self.hierarchy_groups.push({
                                    'name': _t('Other'),
                                    'ids': _.map(_.filter(arg, v => !_.keys(lookup).includes(v['internal_group'])), v => v['id'])
                                });
                                other_accounts_added = true;
                            }
                        })
                    }
                });
            }

            Promise.resolve(prom).then(function() {
                if (!self.hierarchy_groups) {
                    return selectSuper.apply(self, arguments);
                }
                self.$el.empty();
                self._addHierarchy(self.$el, self.hierarchy_groups, 0);
                var value = self.value;
                if (self.field.type === 'many2one' && value) {
                    value = value.data.id;
                }
                self.$el.val(JSON.stringify(value));
            });
        },
        _addHierarchy: function(el, group, level) {
            var self = this;
            _.each(group, function(item) {
                var optgroup = $('<optgroup/>').attr(({
                    'label': $('<div/>').html('&nbsp;'.repeat(6 * level) + item['name']).text(),
                }))
                _.each(item['ids'], function(id) {
                    var value = _.find(self.values, v => v[0] == id)
                    optgroup.append($('<option/>', {
                        value: JSON.stringify(value[0]),
                        text: value[1],
                    }));
                })
                el.append(optgroup)
                if (item['children']) {
                    self._addHierarchy(el, item['children'], level + 1);
                }
            })
        }
    });
    registry.add("account_hierarchy_selection", HierarchySelection);
});
