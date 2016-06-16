odoo.define('web.SearchView', function (require) {
"use strict";

var AutoComplete = require('web.AutoComplete');
var config = require('web.config');
var core = require('web.core');
var data_manager = require('web.data_manager');
var FavoriteMenu = require('web.FavoriteMenu');
var FilterMenu = require('web.FilterMenu');
var GroupByMenu = require('web.GroupByMenu');
var pyeval = require('web.pyeval');
var search_inputs = require('web.search_inputs');
var View = require('web.View');
var Widget = require('web.Widget');
var local_storage = require('web.local_storage');
var _t = core._t;

var Backbone = window.Backbone;

var FacetValue = Backbone.Model.extend({});

var FacetValues = Backbone.Collection.extend({
    model: FacetValue
});

var Facet = Backbone.Model.extend({
    initialize: function (attrs) {
        var values = attrs.values;
        delete attrs.values;

        Backbone.Model.prototype.initialize.apply(this, arguments);

        this.values = new FacetValues(values || []);
        this.values.on('add remove change reset', function (_, options) {
            this.trigger('change', this, options);
        }, this);
    },
    get: function (key) {
        if (key !== 'values') {
            return Backbone.Model.prototype.get.call(this, key);
        }
        return this.values.toJSON();
    },
    set: function (key, value) {
        if (key !== 'values') {
            return Backbone.Model.prototype.set.call(this, key, value);
        }
        this.values.reset(value);
    },
    toJSON: function () {
        var out = {};
        var attrs = this.attributes;
        for(var att in attrs) {
            if (!attrs.hasOwnProperty(att) || att === 'field') {
                continue;
            }
            out[att] = attrs[att];
        }
        out.values = this.values.toJSON();
        return out;
    }
});

var SearchQuery = Backbone.Collection.extend({
    model: Facet,
    initialize: function () {
        Backbone.Collection.prototype.initialize.apply(
            this, arguments);
        this.on('change', function (facet) {
            if(!facet.values.isEmpty()) { return; }

            this.remove(facet, {silent: true});
        }, this);
    },
    add: function (values, options) {
        options = options || {};

        if (!values) {
            values = [];
        } else if (!(values instanceof Array)) {
            values = [values];
        }

        _(values).each(function (value) {
            var model = this._prepareModel(value, options);
            var previous = this.detect(function (facet) {
                return facet.get('category') === model.get('category') &&
                       facet.get('field') === model.get('field');
            });
            if (previous) {
                previous.values.add(model.get('values'), _.omit(options, 'at', 'merge'));
                return;
            }
            Backbone.Collection.prototype.add.call(this, model, options);
        }, this);
        // warning: in backbone 1.0+ add is supposed to return the added models,
        // but here toggle may delegate to add and return its value directly.
        // return value of neither seems actually used but should be tested
        // before change, probably
        return this;
    },
    toggle: function (value, options) {
        options = options || {};

        var facet = this.detect(function (facet) {
            return facet.get('category') === value.category
                && facet.get('field') === value.field;
        });
        if (!facet) {
            return this.add(value, options);
        }

        var changed = false;
        _(value.values).each(function (val) {
            var already_value = facet.values.detect(function (v) {
                return v.get('value') === val.value
                    && v.get('label') === val.label;
            });
            // toggle value
            if (already_value) {
                facet.values.remove(already_value, {silent: true});
            } else {
                facet.values.add(val, {silent: true});
            }
            changed = true;
        });
        // "Commit" changes to values array as a single call, so observers of
        // change event don't get misled by intermediate incomplete toggling
        // states
        facet.trigger('change', facet);
        return this;
    }
});

var InputView = Widget.extend({
    template: 'SearchView.InputView',
    events: {
        focus: function () { this.trigger('focused', this); },
        blur: function () { this.$el.val(''); this.trigger('blurred', this); },
        keydown: 'onKeydown',
    },
    onKeydown: function (e) {
        switch (e.which) {
            case $.ui.keyCode.BACKSPACE:
                if(this.$el.val() === '') {
                    var preceding = this.getParent().siblingSubview(this, -1);
                    if (preceding && (preceding instanceof FacetView)) {
                        preceding.model.destroy();
                    }
                }
                break;

            case $.ui.keyCode.LEFT: // Stop propagation to parent if not at beginning of input value
                if(this.el.selectionStart > 0) {
                    e.stopPropagation();
                }
                break;

            case $.ui.keyCode.RIGHT: // Stop propagation to parent if not at end of input value
                if(this.el.selectionStart < this.$el.val().length) {
                    e.stopPropagation();
                }
                break;
        }
    }
});

var FacetView = Widget.extend({
    template: 'SearchView.FacetView',
    events: {
        'focus': function () { this.trigger('focused', this); },
        'blur': function () { this.trigger('blurred', this); },
        'click': function (e) {
            if ($(e.target).hasClass('o_facet_remove')) {
                this.model.destroy();
                return false;
            }
            this.$el.focus();
            e.stopPropagation();
        },
        'keydown': function (e) {
            var keys = $.ui.keyCode;
            switch (e.which) {
                case keys.BACKSPACE:
                case keys.DELETE:
                    this.model.destroy();
                    return false;
            }
        }
    },
    init: function (parent, model) {
        this._super(parent);
        this.model = model;
        this.model.on('change', this.model_changed, this);
    },
    destroy: function () {
        this.model.off('change', this.model_changed, this);
        this._super();
    },
    start: function () {
        var self = this;
        var $e = this.$('.o_facet_values').last();
        return $.when(this._super()).then(function () {
            return $.when.apply(null, self.model.values.map(function (value, index) {
                if (index > 0) {
                    $('<span/>', {html: self.model.get('separator') || _t(" or ")}).addClass('o_facet_values_sep').appendTo($e);
                }
                return new FacetValueView(self, value).appendTo($e);
            }));
        });
    },
    model_changed: function () {
        this.$el.text(this.$el.text() + '*');
    }
});

var FacetValueView = Widget.extend({
    template: 'SearchView.FacetView.Value',
    init: function (parent, model) {
        this._super(parent);
        this.model = model;
        this.model.on('change', this.model_changed, this);
    },
    destroy: function () {
        this.model.off('change', this.model_changed, this);
        this._super();
    },
    model_changed: function () {
        this.$el.text(this.$el.text() + '*');
    }
});

var SearchView = View.extend({
    events: {
        'click .o_searchview_more': function (e) {
            $(e.target).toggleClass('fa-search-plus fa-search-minus');
            var visible_search_menu = (local_storage.getItem('visible_search_menu') !== 'true');
            local_storage.setItem('visible_search_menu', visible_search_menu);
            this.toggle_buttons();
        },
        'keydown .o_searchview_input, .o_searchview_facet': function (e) {
            switch(e.which) {
                case $.ui.keyCode.LEFT:
                    this.focusPreceding(e.target);
                    e.preventDefault();
                    break;
                case $.ui.keyCode.RIGHT:
                    if(!this.autocomplete.is_expandable()) {
                        this.focusFollowing(e.target);
                    }
                    e.preventDefault();
                    break;
            }
        },
    },
    defaults: _.extend({}, View.prototype.defaults, {
        hidden: false,
        disable_filters: false,
        disable_groupby: false,
        disable_favorites: false,
        disable_custom_filters: false,
    }),
    template: "SearchView",

    /**
     * @constructs SearchView
     * @extends View
     *
     * @param parent
     * @param dataset
     * @param fields_view
     * @param {Object} [options]
     * @param {Boolean} [options.hidden=false] hide the search view
     * @param {Boolean} [options.disable_custom_filters=false] do not load custom filters from ir.filters
     */
    init: function() {
        this._super.apply(this, arguments);
        this.query = undefined;
        this.title = this.options.action && this.options.action.name;
        this.action_id = this.options.action && this.options.action.id;
        this.search_fields = [];
        this.filters = [];
        this.groupbys = [];
        this.visible_filters = (local_storage.getItem('visible_search_menu') === 'true');
        this.input_subviews = []; // for user input in searchbar
        this.search_defaults = this.options.search_defaults || {};
        this.headless = this.options.hidden &&  _.isEmpty(this.search_defaults);
        this.$buttons = this.options.$buttons;

        this.filter_menu = undefined;
        this.groupby_menu = undefined;
        this.favorite_menu = undefined;
    },
    willStart: function () {
        var self = this;
        var def;
        if (!this.options.disable_favorites) {
            def = data_manager.load_filters(this.dataset, this.action_id).then(function (filters) {
                self.favorite_filters = filters;
            });
        }
        return $.when(this._super(), def);
    },
    start: function() {
        if (this.headless) {
            this.do_hide();
        }
        this.toggle_visibility(false);
        this.setup_global_completion();
        this.query = new SearchQuery()
                .on('add change reset remove', this.proxy('do_search'))
                .on('change', this.proxy('renderChangedFacets'))
                .on('add reset remove', this.proxy('renderFacets'));
        this.$('.o_searchview_more')
            .toggleClass('fa-search-minus', this.visible_filters)
            .toggleClass('fa-search-plus', !this.visible_filters);
        var menu_defs = [];
        this.prepare_search_inputs();
        if (this.$buttons) {
            if (!this.options.disable_filters) {
                this.filter_menu = new FilterMenu(this, this.filters);
                menu_defs.push(this.filter_menu.appendTo(this.$buttons));
            }
            if (!this.options.disable_groupby) {
                this.groupby_menu = new GroupByMenu(this, this.groupbys);
                menu_defs.push(this.groupby_menu.appendTo(this.$buttons));
            }
            if (!this.options.disable_favorites) {
                this.favorite_menu = new FavoriteMenu(this, this.query, this.dataset.model, this.action_id, this.favorite_filters);
                menu_defs.push(this.favorite_menu.appendTo(this.$buttons));
            }
        }
        return $.when.apply($, menu_defs).then(this.set_default_filters.bind(this));
    },
    get_title: function() {
        return this.title;
    },
    set_default_filters: function () {
        var self = this,
            default_custom_filter = this.$buttons && this.favorite_menu.get_default_filter();
        if (!self.options.disable_custom_filters && default_custom_filter) {
            return this.favorite_menu.toggle_filter(default_custom_filter, true);
        }
        if (!_.isEmpty(this.search_defaults)) {
            var inputs = this.search_fields.concat(this.filters, this.groupbys),
                search_defaults = _.invoke(inputs, 'facet_for_defaults', this.search_defaults);
            return $.when.apply(null, search_defaults).then(function () {
                self.query.reset(_(arguments).compact(), {preventSearch: true});
            });
        }
        this.query.reset([], {preventSearch: true});
        return $.when();
    },
    /**
     * Performs the search view collection of widget data.
     *
     * If the collection went well (all fields are valid), then triggers
     * :js:func:`instance.web.SearchView.on_search`.
     *
     * If at least one field failed its validation, triggers
     * :js:func:`instance.web.SearchView.on_invalid` instead.
     *
     * @param [_query]
     * @param {Object} [options]
     */
    do_search: function (_query, options) {
        if (options && options.preventSearch) {
            return;
        }
        var search = this.build_search_data();
        this.trigger('search_data', search.domains, search.contexts, search.groupbys);
    },
    /**
     * Extract search data from the view's facets.
     *
     * Result is an object with 3 (own) properties:
     *
     * domains
     *     Array of domains
     * contexts
     *     Array of contexts
     * groupbys
     *     Array of domains, in groupby order rather than view order
     *
     * @return {Object}
     */
    build_search_data: function () {
        var domains = [], contexts = [], groupbys = [];

        this.query.each(function (facet) {
            var field = facet.get('field');
            var domain = field.get_domain(facet);
            if (domain) {
                domains.push(domain);
            }
            var context = field.get_context(facet);
            if (context) {
                contexts.push(context);
            }
            var group_by = field.get_groupby(facet);
            if (group_by) {
                groupbys.push.apply(groupbys, group_by);
            }
        });
        return {
            domains: domains,
            contexts: contexts,
            groupbys: groupbys,
        };
    },
    toggle_visibility: function (is_visible) {
        this.do_toggle(!this.headless && is_visible);
        if (this.$buttons) {
            this.$buttons.toggle(!this.headless && is_visible && this.visible_filters);
        }
        if (!config.device.touch && config.device.size_class >= config.device.SIZES.SM) {
            this.$('input').focus();
        }
    },
    toggle_buttons: function (is_visible) {
        this.visible_filters = is_visible || !this.visible_filters;
        if (this.$buttons)  {
            this.$buttons.toggle(this.visible_filters);
        }
    },
    /**
     * Sets up search view's view-wide auto-completion widget
     */
    setup_global_completion: function () {
        var self = this;
        this.autocomplete = new AutoComplete(this, {
            source: this.proxy('complete_global_search'),
            select: this.proxy('select_completion'),
            get_search_string: function () {
                return self.$('.o_searchview_input').val().trim();
            },
        });
        this.autocomplete.appendTo(this.$el);
    },
    /**
     * Provide auto-completion result for req.term (an array to `resp`)
     *
     * @param {Object} req request to complete
     * @param {String} req.term searched term to complete
     * @param {Function} resp response callback
     */
    complete_global_search:  function (req, resp) {
        var inputs = this.search_fields.concat(this.filters, this.groupbys);
        $.when.apply(null, _(inputs).chain()
            .filter(function (input) { return input.visible(); })
            .invoke('complete', req.term)
            .value()).then(function () {
                resp(_(arguments).chain()
                    .compact()
                    .flatten(true)
                    .value());
                });
    },
    /**
     * Action to perform in case of selection: create a facet (model)
     * and add it to the search collection
     *
     * @param {Object} e selection event, preventDefault to avoid setting value on object
     * @param {Object} ui selection information
     * @param {Object} ui.item selected completion item
     */
    select_completion: function (e, ui) {
        e.preventDefault();
        if(ui.item.facet.values && ui.item.facet.values.length && String(ui.item.facet.values[0].value).trim() !== "") {
            this.query.add(ui.item.facet);
        } else {
            this.query.trigger('add');
        }
    },
    subviewForRoot: function (subview_root) {
        return _(this.input_subviews).detect(function (subview) {
            return subview.$el[0] === subview_root;
        });
    },
    siblingSubview: function (subview, direction, wrap_around) {
        var index = _(this.input_subviews).indexOf(subview) + direction;
        if (wrap_around && index < 0) {
            index = this.input_subviews.length - 1;
        } else if (wrap_around && index >= this.input_subviews.length) {
            index = 0;
        }
        return this.input_subviews[index];
    },
    focusPreceding: function (subview_root) {
        return this.siblingSubview(
            this.subviewForRoot(subview_root), -1, true)
                .$el.focus();
    },
    focusFollowing: function (subview_root) {
        return this.siblingSubview(
            this.subviewForRoot(subview_root), +1, true)
                .$el.focus();
    },
    /**
     * @param {openerp.web.search.SearchQuery | undefined} Undefined if event is change
     * @param {openerp.web.search.Facet}
     * @param {Object} [options]
     */
    renderFacets: function (collection, model, options) {
        var self = this;
        var started = [];
        _.invoke(this.input_subviews, 'destroy');
        this.input_subviews = [];

        this.query.each(function (facet) {
            var f = new FacetView(this, facet);
            started.push(f.appendTo(self.$el));
            self.input_subviews.push(f);
        }, this);
        var i = new InputView(this);
        started.push(i.appendTo(self.$el));
        self.input_subviews.push(i);
        _.each(this.input_subviews, function (childView) {
            childView.on('focused', self, self.proxy('childFocused'));
            childView.on('blurred', self, self.proxy('childBlurred'));
        });

        $.when.apply(null, started).then(function () {
            _.last(self.input_subviews).$el.focus();
        });
    },
    childFocused: function () {
        this.$el.addClass('active');
    },
    childBlurred: function () {
        this.$el.val('').removeClass('active').trigger('blur');
        this.autocomplete.close();
    },
    /**
     * Call the renderFacets method with the correct arguments.
     * This is due to the fact that change events are called with two arguments
     * (model, options) while add, reset and remove events are called with
     * (collection, model, options) as arguments
     */
    renderChangedFacets: function (model, options) {
        this.renderFacets(undefined, model, options);
    },
    // it should parse the arch field of the view, instantiate the corresponding
    // filters/fields, and put them in the correct variables:
    // * this.search_fields is a list of all the fields,
    // * this.filters: groups of filters
    // * this.group_by: group_bys
    prepare_search_inputs: function () {
        var self = this,
            arch = this.fields_view.arch;

        var filters = [].concat.apply([], _.map(arch.children, function (item) {
            return item.tag !== 'group' ? eval_item(item) : item.children.map(eval_item);
        }));
        function eval_item (item) {
            var category = 'filters';
            if (item.attrs.context) {
                try {
                    var context = pyeval.eval('context', item.attrs.context);
                    if (context.group_by) {
                        category = 'group_by';
                    }
                } catch (e) {}
            }
            return {
                item: item,
                category: category,
            };
        }
        var current_group = [],
            current_category = 'filters',
            categories = {filters: this.filters, group_by: this.groupbys};

        _.each(filters.concat({category:'filters', item: 'separator'}), function (filter) {
            if (filter.item.tag === 'filter' && filter.category === current_category) {
                return current_group.push(new search_inputs.Filter(filter.item, self));
            }
            if (current_group.length) {
                var group = new search_inputs.FilterGroup(current_group, self);
                categories[current_category].push(group);
                current_group = [];
            }
            if (filter.item.tag === 'field') {
                var attrs = filter.item.attrs;
                var field = self.fields_view.fields[attrs.name];

                // M2O combined with selection widget is pointless and broken in search views,
                // but has been used in the past for unsupported hacks -> ignore it
                if (field.type === "many2one" && attrs.widget === "selection") {
                    attrs.widget = undefined;
                }

                var Obj = core.search_widgets_registry.get_any([attrs.widget, field.type]);
                if (Obj) {
                    self.search_fields.push(new (Obj) (filter.item, field, self));
                }
            }
            if (filter.item.tag === 'filter') {
                current_group.push(new search_inputs.Filter(filter.item, self));
            }
            current_category = filter.category;
        });
    },
});

_.extend(SearchView, {
    SearchQuery: SearchQuery,
    Facet: Facet,
});

return SearchView;

});
