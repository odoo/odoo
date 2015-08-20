odoo.define('web.FavoriteMenu', function (require) {
"use strict";

var core = require('web.core');
var Model = require('web.DataModel');
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
        'click .oe-save-search a': function () {
            this.toggle_save_menu();
        },
        'click .oe-save-name button': 'save_favorite',
        'hidden.bs.dropdown': 'close_menus',
        'keyup .oe-save-name input': function (ev) {
            if (ev.which === $.ui.keyCode.ENTER) {
                this.save_favorite();
            }
        },
    },
    init: function (parent, query, target_model, action_id) {
        this._super.apply(this,arguments);
        this.searchview = parent;
        this.query = query;
        this.target_model = target_model;
        this.model = new Model('ir.filters');
        this.filters = {};
        this.$filters = {};
        this.action_id = action_id;
    },
    start: function () {
        var self = this;
        this.$save_search = this.$('.oe-save-search');
        this.$save_name = this.$('.oe-save-name');
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
        return this.model.call('get_filters', [this.target_model, this.action_id],
                               {context: this.searchview.dataset.context})
            .done(this.proxy('prepare_dropdown_menu'));
    },
    prepare_dropdown_menu: function (filters) {
        filters.map(this.append_filter.bind(this));
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
            model_id: this.searchview.dataset.model,
            context: results.context,
            domain: results.domain,
            sort: JSON.stringify(this.searchview.dataset._sort),
            is_default: default_filter,
            action_id: this.action_id,
        };
        return this.model.call('create_or_replace', [filter]).done(function (id) {
            filter.id = id;
            self.toggle_save_menu(false);
            self.$save_name.find('input').val('').prop('checked', false);
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
    append_filter: function (filter) {
        var self = this,
            key = this.key_for(filter),
            $filter;

        this.$divider.show();
        if (key in this.$filters) {
            $filter = this.$filters[key];
        } else {
            this.filters[key] = filter;
            $filter = $('<li></li>')
                .insertBefore(this.$divider)
                .toggleClass('oe_searchview_custom_default', filter.is_default)
                .append($('<a>').text(filter.name));

            this.$filters[key] = $filter;
            this.$filters[key].addClass(filter.user_id ? 'oe_searchview_custom_private'
                                         : 'oe_searchview_custom_public');
            $('<span>')
                .addClass('fa fa-trash-o remove-filter')
                .click(function (event) {
                    event.stopImmediatePropagation();
                    self.remove_filter(filter, $filter, key);
                })
                .appendTo($filter);
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
        this.model.call('unlink', [filter.id]).done(function () {
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

var search_filters = require('web.search_filters');
var search_inputs = require('web.search_inputs');
var Widget = require('web.Widget');

return Widget.extend({
    template: 'SearchView.FilterMenu',
    events: {
        'click .oe-add-filter': function () {
            this.toggle_custom_filter_menu();
        },
        'click li': function (event) {event.stopImmediatePropagation();},
        'hidden.bs.dropdown': function () {
            this.toggle_custom_filter_menu(false);
        },
        'click .oe-add-condition': 'append_proposition',
        'click .oe-apply-filter': 'commit_search',
        'keyup .searchview_extended_prop_value': function (ev) {
            if (ev.which === $.ui.keyCode.ENTER) {
                this.commit_search();
            }
        },
    },
    init: function (parent, filters, fields_def) {
        this._super(parent);
        this.filters = filters || [];
        this.searchview = parent;
        this.propositions = [];
        this.fields_def = fields_def.then(function (data) {
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
    },
    start: function () {
        var self = this;
        this.$menu = this.$('.filters-menu');
        this.$add_filter = this.$('.oe-add-filter');
        this.$apply_filter = this.$('.oe-apply-filter');
        this.$add_filter_menu = this.$('.oe-add-filter-menu');
        _.each(this.filters, function (group) {
            if (group.is_visible()) {
                group.insertBefore(self.$add_filter);
                $('<li class="divider">').insertBefore(self.$add_filter);
            }
        });
        this.append_proposition().then(function (prop) {
            prop.$el.hide();
        });
    },
    toggle_custom_filter_menu: function (is_open) {
        this.$add_filter
            .toggleClass('o_closed_menu', !(_.isUndefined(is_open)) ? !is_open : undefined)
            .toggleClass('o_open_menu', is_open);
        this.$add_filter_menu.toggle(is_open);
        if (this.$add_filter.hasClass('o_closed_menu') && (!this.propositions.length)) {
            this.append_proposition();
        }
        this.$('.oe-filter-condition').toggle(is_open);
    },
    append_proposition: function () {
        var self = this;
        return this.fields_def.then(function (fields) {
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

var Widget = require('web.Widget');
var core = require('web.core');
var search_inputs = require('web.search_inputs');

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
        'click .add-custom-group a': function () {
            this.toggle_add_menu();
        },
    },
    init: function (parent, groups, fields_def) {
        this._super(parent);
        this.groups = groups || [];
        this.groupable_fields = [];
        this.searchview = parent;
        this.fields_def = fields_def.then(this.proxy('get_groupable_fields'));
    },
    start: function () {
        var self = this;
        this.$menu = this.$('.group-by-menu');
        var divider = this.$menu.find('.divider');
        _.invoke(this.groups, 'insertBefore', divider);
        if (this.groups.length) {
            divider.show();
        }
        this.$add_group = this.$menu.find('.add-custom-group');
        this.fields_def.then(function () {
            self.$menu.append(QWeb.render('GroupByMenuSelector', self));
            self.$add_group_menu = self.$('.oe-add-group');
            self.$group_selector = self.$('.oe-group-selector');
            self.$('.oe-select-group').click(function () {
                self.toggle_add_menu(false);
                var field = self.$group_selector.find(':selected').data('name');
                self.add_groupby_to_menu(field);
            });
        });
    },
    get_groupable_fields: function (fields) {
        var groupable_types = ['many2one', 'char', 'boolean', 'selection', 'date', 'datetime'];
        var filter_group_field = _.filter(fields, function(field, name) {
            if (field.store && _.contains(groupable_types, field.type)) {
                field.name = name;
                return field;
            }
        });
        this.groupable_fields = _.sortBy(filter_group_field, 'string');
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
            name: _.find(this.groupable_fields, {name: field_name}).string,
        }}, this.searchview);
        var group = new search_inputs.FilterGroup([filter], this.searchview),
            divider = this.$('.divider').show();
        group.insertBefore(divider);
        group.toggle(filter);
    },
});

});
