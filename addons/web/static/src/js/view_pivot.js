/*---------------------------------------------------------
 * Odoo Pivot Table view
 *---------------------------------------------------------*/

(function () {
'use strict';

var instance = openerp,
    _lt = instance.web._lt,
    _t = instance.web._t,
    QWeb = instance.web.qweb;

instance.web.views.add('pivot', 'instance.web.PivotView');

instance.web.PivotView = instance.web.View.extend({
    template: 'PivotView',
    display_name: _lt('Pivot'),
    view_type: 'pivot',

    init: function(parent, dataset, view_id, options) {
        this._super(parent, dataset, view_id, options);
        this.model = new instance.web.Model(dataset.model, {group_by_no_leaf: true});
        this.action_manager = parent.action_manager;

        this.$buttons = options.$buttons;
        this.fields = {};
        this.measures = {};
        this.groupable_fields = {};

        this.row_groupbys = [];
        this.col_groupbys = [];
        this.active_measures = [];
    },
    start: function () {
        var self = this,
            load_fields = this.model.call('fields_get', [])
                .then(this.prepare_fields.bind(this));

        return $.when(this._super(), load_fields).then(function () {
            var context = {measures: _.pairs(self.measures)};
            self.$buttons.html(QWeb.render('PivotView.buttons', self), context);
        });
    },
    view_loading: function (fvg) {
        var self = this;
        this.do_push_state({});
        fvg.arch.children.forEach(function (field) {
            var name = field.attrs.name + (field.attrs.interval || '');
            //noinspection FallThroughInSwitchStatementJS
            switch (field.attrs.type) {
            case 'measure':
                self.active_measures.push(name);
                break;
            case 'col':
                self.col_groupbys.push(name);
                break;
            default:
                if ('operator' in field.attrs) {
                    self.active_measures.push(name);
                    break;
                }
            case 'row':
                self.row_groupbys.push(name);
            }
        });
    },
    prepare_fields: function (fields) {
        var self = this,
            groupable_types = ['many2one', 'char', 'boolean', 
                               'selection', 'date', 'datetime'];
        this.fields = fields;
        _.each(fields, function (field, name) {
            if ((name !== 'id') && (field.store === true)) {
                if (field.type === 'integer' || field.type === 'float') {
                    self.measures[name] = field;
                }
                if (_.contains(groupable_types, field.type)) {
                    self.groupable_fields[name] = field;
                }
            }
        });
    },
    do_search: function (domain, context, group_by) {
    },
});


})();

