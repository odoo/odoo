odoo.define('web.FilterMenu', function (require) {
"use strict";

var search_filters = require('web.search_filters');
var search_inputs = require('web.search_inputs');
var Widget = require('web.Widget');

return Widget.extend({
    template: 'SearchView.FilterMenu',
    events: {
        'click .o_add_filter': function (event) {
            event.preventDefault();
            this.toggle_custom_filter_menu();
        },
        'click li': function (event) {
            event.preventDefault();
            event.stopImmediatePropagation();
        },
        'hidden.bs.dropdown': function () {
            this.toggle_custom_filter_menu(false);
        },
        'click .o_add_condition': 'append_proposition',
        'click .o_apply_filter': 'commit_search',
        'keyup .o_searchview_extended_prop_value': function (ev) {
            if (ev.which === $.ui.keyCode.ENTER) {
                this.commit_search();
            }
        },
    },
    init: function (parent, filters, fields) {
        this._super(parent);
        this.filters = filters || [];
        this.searchview = parent;
        this.propositions = [];
        this.custom_filters_open = false;
        this.fields = _.pick(fields, function (field, name) {
            return field.selectable !== false && name !== 'id';
        });
        this.fields.id = { string: 'ID', type: 'id', searchable: true };
    },
    start: function () {
        var self = this;
        this.$menu = this.$('.o_filters_menu');
        this.$add_filter = this.$('.o_add_filter');
        this.$apply_filter = this.$('.o_apply_filter');
        this.$add_filter_menu = this.$('.o_add_filter_menu');
        _.each(this.filters, function (group) {
            if (group.is_visible()) {
                group.insertBefore(self.$add_filter);
                $('<li class="divider">').insertBefore(self.$add_filter);
            }
        });
    },
    toggle_custom_filter_menu: function (is_open) {
        var self = this;
        this.custom_filters_open = !_.isUndefined(is_open) ? is_open : !this.custom_filters_open;
        var def;
        if (this.custom_filters_open && !this.propositions.length) {
            def = this.append_proposition();
        }
        $.when(def).then(function () {
            self.$add_filter
                .toggleClass('o_closed_menu', !self.custom_filters_open)
                .toggleClass('o_open_menu', self.custom_filters_open);
            self.$add_filter_menu.toggle(self.custom_filters_open);
            self.$('.o_filter_condition').toggle(self.custom_filters_open);
        });
    },
    append_proposition: function () {
        var prop = new search_filters.ExtendedSearchProposition(this, this.fields);
        this.propositions.push(prop);
        this.$apply_filter.prop('disabled', false);
        return prop.insertBefore(this.$add_filter_menu);
    },
    remove_proposition: function (prop) {
        this.propositions = _.without(this.propositions, prop);
        if (!this.propositions.length) {
            this.$apply_filter.prop('disabled', true);
        }
        prop.destroy();
    },
    commit_search: function () {
        var filters = _.invoke(this.propositions, 'get_filter'),
            filters_widgets = _.map(filters, function (filter) {
                return new search_inputs.Filter(filter, this);
            }),
            filter_group = new search_inputs.FilterGroup(filters_widgets, this.searchview),
            facets = filters_widgets.map(function (filter) {
                return filter_group.make_facet([filter_group.make_value(filter)]);
            });
        filter_group.insertBefore(this.$add_filter);
        $('<li class="divider">').insertBefore(this.$add_filter);
        this.searchview.query.add(facets, {silent: true});
        this.searchview.query.trigger('reset');

        _.invoke(this.propositions, 'destroy');
        this.propositions = [];
        this.append_proposition();
        this.toggle_custom_filter_menu(false);
    },
});

});
