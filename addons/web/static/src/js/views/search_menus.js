odoo.define('web.FavoriteMenu', function (require) {
"use strict";

var core = require('web.core');
var data_manager = require('web.data_manager');
var pyeval = require('web.pyeval');
var session = require('web.session');
var Widget = require('web.Widget');

var _t = core._t;

return Widget.extend({
    template: 'SearchView.FavoriteMenu',
    events: {
        'click li': function (event) {
            event.stopImmediatePropagation();
        },
        'click li a': function (event) {
            event.preventDefault();
        },
        'click .o_save_search a': function (event) {
            event.preventDefault();
            this.toggle_save_menu();
        },
        'click .o_save_name button': 'save_favorite',
        'hidden.bs.dropdown': 'close_menus',
        'keyup .o_save_name input': function (ev) {
            if (ev.which === $.ui.keyCode.ENTER) {
                this.save_favorite();
            }
        },
    },
    init: function (parent, query, target_model, action_id, filters) {
        this._super.apply(this,arguments);
        this.searchview = parent;
        this.query = query;
        this.target_model = target_model;
        this.action_id = action_id;
        this.filters = {};
        _.each(filters, this.add_filter.bind(this));
    },
    start: function () {
        var self = this;
        this.$filters = {};
        this.$save_search = this.$('.o_save_search');
        this.$save_name = this.$('.o_save_name');
        this.$inputs = this.$save_name.find('input');
        this.$divider = this.$('.divider');
        this.$inputs.eq(0).val(this.searchview.get_title());
        var $shared_filter = this.$inputs.eq(1),
            $default_filter = this.$inputs.eq(2);
        $shared_filter.click(function () {$default_filter.prop('checked', false);});
        $default_filter.click(function () {$shared_filter.prop('checked', false);});

        this.query
            .on('remove', function (facet) {
                if (facet.get('is_custom_filter')) {
                    self.clear_selection();
                }
            })
            .on('reset', this.proxy('clear_selection'));

        _.each(this.filters, this.append_filter.bind(this));

        return this._super();
    },
    toggle_save_menu: function (is_open) {
        this.$save_search
            .toggleClass('o_closed_menu', !(_.isUndefined(is_open)) ? !is_open : undefined)
            .toggleClass('o_open_menu', is_open);
        this.$save_name.toggle(is_open);
        if (this.$save_search.hasClass('o_open_menu')) {
            this.$save_name.find('input').first().focus();
        }
    },
    close_menus: function () {
        this.toggle_save_menu(false);
    },
    save_favorite: function () {
        var self = this,
            filter_name = this.$inputs[0].value,
            default_filter = this.$inputs[1].checked,
            shared_filter = this.$inputs[2].checked;
        if (!filter_name.length){
            this.do_warn(_t("Error"), _t("Filter name is required."));
            this.$inputs.first().focus();
            return;
        }
        if (_.chain(this.filters)
                .pluck('name')
                .contains(filter_name).value()) {
            this.do_warn(_t("Error"), _t("Filter with same name already exists."));
            this.$inputs.first().focus();
            return;
        }
        var search = this.searchview.build_search_data(),
            view_manager = this.findAncestor(function (a) {
                // HORRIBLE HACK. PLEASE SAVE ME FROM MYSELF (BUT IN A PAINLESS WAY IF POSSIBLE)
                return 'active_view' in a;
            }),
            view_context = view_manager ? view_manager.active_view.controller.get_context() : {},
            results = pyeval.sync_eval_domains_and_contexts({
                domains: search.domains,
                contexts: search.contexts.concat(view_context || []),
                group_by_seq: search.groupbys || [],
            });
        if (!_.isEmpty(results.group_by)) {
            results.context.group_by = results.group_by;
        }
        // Don't save user_context keys in the custom filter, otherwise end
        // up with e.g. wrong uid or lang stored *and used in subsequent
        // reqs*
        var ctx = results.context;
        _(_.keys(session.user_context)).each(function (key) {
            delete ctx[key];
        });
        var filter = {
            name: filter_name,
            user_id: shared_filter ? false : session.uid,
            model_id: this.target_model,
            context: results.context,
            domain: results.domain,
            sort: JSON.stringify(this.searchview.dataset._sort),
            is_default: default_filter,
            action_id: this.action_id,
        };
        return data_manager.create_filter(filter).done(function (id) {
            filter.id = id;
            self.toggle_save_menu(false);
            self.$save_name.find('input').val('').prop('checked', false);
            self.add_filter(filter);
            self.append_filter(filter);
            self.toggle_filter(filter, true);
        });
    },
    get_default_filter: function () {
        var personal_filter = _.find(this.filters, function (filter) {
            return filter.user_id && filter.is_default;
        });
        if (personal_filter) {
            return personal_filter;
        }
        return _.find(this.filters, function (filter) {
            return !filter.user_id && filter.is_default;
        });
    },
    /**
     * Generates a mapping key (in the filters and $filter mappings) for the
     * filter descriptor object provided (as returned by ``get_filters``).
     *
     * The mapping key is guaranteed to be unique for a given (user_id, name)
     * pair.
     *
     * @param {Object} filter
     * @param {String} filter.name
     * @param {Number|Pair<Number, String>} [filter.user_id]
     * @return {String} mapping key corresponding to the filter
     */
    key_for: function (filter) {
        var user_id = filter.user_id,
            action_id = filter.action_id,
            uid = (user_id instanceof Array) ? user_id[0] : user_id,
            act_id = (action_id instanceof Array) ? action_id[0] : action_id;
        return _.str.sprintf('(%s)(%s)%s', uid, act_id, filter.name);
    },
    /**
     * Generates a :js:class:`~instance.web.search.Facet` descriptor from a
     * filter descriptor
     *
     * @param {Object} filter
     * @param {String} filter.name
     * @param {Object} [filter.context]
     * @param {Array} [filter.domain]
     * @return {Object}
     */
    facet_for: function (filter) {
        return {
            category: _t("Custom Filter"),
            icon: 'fa-star',
            field: {
                get_context: function () { return filter.context; },
                get_groupby: function () { return [filter.context]; },
                get_domain: function () { return filter.domain; }
            },
            _id: filter.id,
            is_custom_filter: true,
            values: [{label: filter.name, value: null}]
        };
    },
    clear_selection: function () {
        this.$('li.selected').removeClass('selected');
    },
    /**
     * Adds a filter description to the filters dict
     * @param {Object} [filter] the filter description
     */
    add_filter: function (filter) {
        this.filters[this.key_for(filter)] = filter;
    },
    /**
     * Creates a $filter JQuery node, adds it to the $filters dict and appends it to the filter menu
     * @param {Object} [filter] the filter description
     */
    append_filter: function (filter) {
        var self = this;
        var key = this.key_for(filter);

        this.$divider.show();
        if (!(key in this.$filters)) {
            var $filter = $('<li>')
                .addClass(filter.user_id ? 'o-searchview-custom-private'
                                         : 'o-searchview-custom-public')
                .append($('<a>', {'href': '#'}).text(filter.name))
                .append($('<span>', {
                    class: 'fa fa-trash-o o-remove-filter',
                    on: {
                        click: function (event) {
                            event.stopImmediatePropagation();
                            self.remove_filter(filter, $filter, key);
                        },
                    },
                }))
                .insertBefore(this.$divider);
            this.$filters[key] = $filter;
        }
        this.$filters[key].unbind('click').click(function () {
            self.toggle_filter(filter);
        });
    },
    toggle_filter: function (filter, preventSearch) {
        var current = this.query.find(function (facet) {
            return facet.get('_id') === filter.id;
        });
        if (current) {
            this.query.remove(current);
            this.$filters[this.key_for(filter)].removeClass('selected');
            return;
        }
        this.query.reset([this.facet_for(filter)], {
            preventSearch: preventSearch || false});

        // Load sort settings on view
        if (!_.isUndefined(filter.sort)){
            var sort_items = JSON.parse(filter.sort);
            this.searchview.dataset.set_sort(sort_items);
        }

        this.$filters[this.key_for(filter)].addClass('selected');
    },
    remove_filter: function (filter, $filter, key) {
        var self = this;
        var global_warning = _t("This filter is global and will be removed for everybody if you continue."),
            warning = _t("Are you sure that you want to remove this filter?");
        if (!confirm(filter.user_id ? warning : global_warning)) {
            return;
        }
        return data_manager
            .delete_filter(filter)
            .done(function () {
                $filter.remove();
                delete self.$filters[key];
                delete self.filters[key];
                if (_.isEmpty(self.filters)) {
                    self.$divider.hide();
                }
            });
    },
});

});

odoo.define('web.FilterMenu', function (require) {
"use strict";

var data_manager = require('web.data_manager');
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
    init: function (parent, filters) {
        this._super(parent);
        this.filters = filters || [];
        this.searchview = parent;
        this.propositions = [];
        this.custom_filters_open = false;
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
    get_fields: function () {
        if (!this._fields_def) {
            this._fields_def = data_manager.load_fields(this.searchview.dataset).then(function (data) {
                var fields = {
                    id: { string: 'ID', type: 'id', searchable: true }
                };
                _.each(data, function(field_def, field_name) {
                    if (field_def.selectable !== false && field_name !== 'id') {
                        fields[field_name] = field_def;
                    }
                });
                return fields;
            });
        }
        return this._fields_def;
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
        var self = this;
        return this.get_fields().then(function (fields) {
            var prop = new search_filters.ExtendedSearchProposition(self, fields);
            self.propositions.push(prop);
            prop.insertBefore(self.$add_filter_menu);
            self.$apply_filter.prop('disabled', false);
            return prop;
        });
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

odoo.define('web.GroupByMenu', function (require) {
"use strict";

var core = require('web.core');
var data_manager = require('web.data_manager');
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
    init: function (parent, groups) {
        this._super(parent);
        this.groups = groups || [];
        this.groupable_fields = [];
        this.searchview = parent;
    },
    start: function () {
        this.$menu = this.$('.o_group_by_menu');
        var divider = this.$menu.find('.divider');
        _.invoke(this.groups, 'insertBefore', divider);
        if (this.groups.length) {
            divider.show();
        }
        this.$add_group = this.$menu.find('.o_add_custom_group');
    },
    get_fields: function () {
        var self = this;
        if (!this._fields_def) {
            this._fields_def = data_manager.load_fields(this.searchview.dataset).then(function (fields) {
                var groupable_types = ['many2one', 'char', 'boolean', 'selection', 'date', 'datetime'];
                var filter_group_field = _.filter(fields, function(field, name) {
                    if (field.store && _.contains(groupable_types, field.type)) {
                        field.name = name;
                        return field;
                    }
                });
                self.groupable_fields = _.sortBy(filter_group_field, 'string');

                self.$menu.append(QWeb.render('GroupByMenuSelector', self));
                self.$add_group_menu = self.$('.o_add_group');
                self.$group_selector = self.$('.o_group_selector');
                self.$('.o_select_group').click(function () {
                    self.toggle_add_menu(false);
                    var field = self.$group_selector.find(':selected').data('name');
                    self.add_groupby_to_menu(field);
                });
            });
        }
        return this._fields_def;
    },
    toggle_add_menu: function (is_open) {
        var self = this;
        this.get_fields().then(function () {
            self.$add_group
                .toggleClass('o_closed_menu', !(_.isUndefined(is_open)) ? !is_open : undefined)
                .toggleClass('o_open_menu', is_open);
            self.$add_group_menu.toggle(is_open);
            if (self.$add_group.hasClass('o_open_menu')) {
                self.$group_selector.focus();
            }
        });
    },
    add_groupby_to_menu: function (field_name) {
        var filter = new search_inputs.Filter({attrs:{
            context:"{'group_by':'" + field_name + "''}",
            name: _.find(this.groupable_fields, {name: field_name}).string,
        }}, this.searchview);
        var group = new search_inputs.FilterGroup([filter], this.searchview),
            divider = this.$('.divider').show();
        group.insertBefore(divider);
        group.toggle(filter);
    },
});

});
