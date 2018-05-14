odoo.define('web.GroupByMenu', function (require) {
"use strict";

var config = require('web.config');
var core = require('web.core');
var search_inputs = require('web.search_inputs');
var Widget = require('web.Widget');

var QWeb = core.qweb;

return Widget.extend({
    template: 'SearchView.GroupByMenu',
    events: {
        'click li': function (event) {
            event.stopImmediatePropagation();
        },
        'hidden.bs.dropdown': function () {
            this.toggle_add_menu(false);
        },
        'click .o_add_custom_group a': function (event) {
            event.preventDefault();
            this.toggle_add_menu();
        },
    },
    init: function (parent, groups, fields) {
        var self = this;
        this._super(parent);
        this.searchview = parent;
        this.isMobile = config.device.isMobile;
        this.groups = groups || [];
        this.groupableFields = [];
        var groupable_types = ['many2one', 'char', 'boolean', 'selection', 'date', 'datetime'];
        _.each(fields, function (field, name) {
            if (field.sortable && _.contains(groupable_types, field.type)) {
                self.groupableFields.push(_.extend({}, field, {name: name}));
            }
        });
        self.groupableFields = _.sortBy(this.groupableFields, 'string');
    },
    start: function () {
        var self = this;
        this.$menu = this.$('.o_group_by_menu');
        var divider = this.$menu.find('.divider');
        _.invoke(this.groups, 'insertBefore', divider);
        if (this.groups.length) {
            divider.show();
        }
        this.$add_group = this.$menu.find('.o_add_custom_group');
        this.$menu.append(QWeb.render('GroupByMenuSelector', this));
        this.$add_group_menu = this.$('.o_add_group');
        this.$group_selector = this.$('.o_group_selector');
        this.$('.o_select_group').click(function () {
            self.toggle_add_menu(false);
            var field = self.$group_selector.find(':selected').data('name');
            self.add_groupby_to_menu(field);
        });
    },
    toggle_add_menu: function (is_open) {
        this.$add_group
            .toggleClass('o_closed_menu', !(_.isUndefined(is_open)) ? !is_open : undefined)
            .toggleClass('o_open_menu', is_open);
        this.$add_group_menu.toggle(is_open);
        if (this.$add_group.hasClass('o_open_menu')) {
            this.$group_selector.focus();
        }
    },
    add_groupby_to_menu: function (field_name) {
        var filter = new search_inputs.Filter({attrs:{
            context:"{'group_by':'" + field_name + "''}",
            name: _.find(this.groupableFields, {name: field_name}).string,
        }}, this.searchview);
        var group = new search_inputs.FilterGroup([filter], this.searchview),
            divider = this.$('.divider').show();
        group.insertBefore(divider);
        group.toggle(filter);
    },
});

});