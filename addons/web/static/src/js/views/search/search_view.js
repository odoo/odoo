odoo.define('web.SearchView', function (require) {
"use strict";

var AutoComplete = require('web.AutoComplete');
var config = require('web.config');
var core = require('web.core');
var Domain = require('web.Domain');
var FavoriteMenu = require('web.FavoriteMenu');
var FiltersMenu = require('web.FiltersMenu');
var GroupByMenu = require('web.GroupByMenu');
var pyUtils = require('web.py_utils');
var search_inputs = require('web.search_inputs');
var TimeRangeMenu = require('web.TimeRangeMenu');
var TimeRangeMenuOptions = require('web.TimeRangeMenuOptions');
var utils = require('web.utils');
var Widget = require('web.Widget');

var _t = core._t;
var ComparisonOptions = TimeRangeMenuOptions.ComparisonOptions;
var PeriodOptions = TimeRangeMenuOptions.PeriodOptions;

var Backbone = window.Backbone;

var FacetValue = Backbone.Model.extend({});

var FacetValues = Backbone.Collection.extend({
    model: FacetValue
});

var DEFAULT_INTERVAL = 'month';
var DEFAULT_PERIOD = 'this_month';

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
        'blur': function () {
            this.trigger('blurred', this); },
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
    /*
     * @param {Widget} parent
     * @param {Object} model
     * @param {Object} intervalMapping, a key is a field name and the corresponding value
     *                   is the current interval used
     *                   (necessarily the field is of type 'date' or 'datetime')
     * @param {Object} periodMapping, a key is a field name and the corresponding value
     *                   is the current period used
     *                   (necessarily the field is of type 'date' or 'datetime')
     */
    init: function (parent, model, intervalMapping, periodMapping) {
        this._super(parent);
        this.model = model;
        this.intervalMapping = intervalMapping;
        this.periodMapping = periodMapping;
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
                var couple;
                var option;
                if (value.attributes.value && value.attributes.value.attrs) {
                    if (value.attributes.value.attrs.isPeriod) {
                        couple = _.findWhere(self.periodMapping, {filter: value.attributes.value});
                        option = couple ? couple.period : value.attributes.value.attrs.default_period;
                    }
                    if (value.attributes.value.attrs.isDate) {
                        couple = _.findWhere(self.intervalMapping, {groupby: value.attributes.value});
                        option = couple ?
                                    couple.interval :
                                    (value.attributes.value.attrs.defaultInterval || DEFAULT_INTERVAL);
                    }
                }
                return new FacetValueView(self, value, option).appendTo($e);
            }));
        });
    },
    model_changed: function () {
        this.$el.text(this.$el.text() + '*');
    }
});

var FacetValueView = Widget.extend({
    template: 'SearchView.FacetView.Value',
    /*
     * @param {Widget} parent
     * @param {Object} model
     * @param {Object} option (optional) is used in case the facet value
     *                  corresponds to a groupby with an associated 'date'
     *                  'datetime' field.
     * @param {Object} comparison (optional) is used in case the facet value
     *                  comes from the time range menu and comparison is active
     */
    init: function (parent, model, option) {
        this._super(parent);
        this.model = model;

        var optionDescription = _.extend({}, {
            day: 'Day',
            week: 'Week',
            month: 'Month',
            quarter: 'Quarter',
            year: 'Year',
        }, {
            today: 'Today',
            this_week: 'This Week',
            this_month: 'This Month',
            this_quarter: 'This Quarter',
            this_year: 'This Year',
            yesterday: 'Yesterday',
            last_week: 'Last Week',
            last_month: 'Last Month',
            last_quarter: 'Last Quarter',
            last_year: 'Last Year',
            last_7_days: 'Last 7 Days',
            last_30_days: 'Last 30 Days',
            last_365_days: 'Last 365 Days',
        });
        if (option) {
            var optionLabel = optionDescription[option];
            this.optionLabel = _t(optionLabel);
        }
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

var SearchView = Widget.extend({
    events: {
        'click .o_searchview_more': function (e) {
            $(e.target).toggleClass('fa-search-plus fa-search-minus');
            var visibleSearchMenu = this.call('local_storage', 'getItem', 'visible_search_menu');
            this.call('local_storage', 'setItem', 'visible_search_menu', visibleSearchMenu === false);
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
                case $.ui.keyCode.DOWN:
                    if (!this.autocomplete.is_expanded()) {
                        e.preventDefault();
                        this.trigger_up('navigation_move', {direction: 'down'});
                        break;
                    }
            }
        },
    },
    custom_events: {
        menu_item_toggled: '_onItemToggled',
        item_option_changed: '_onItemOptionChanged',
        new_groupby: '_onNewGroupby',
        new_filters: '_onNewFilters',
        time_range_modified: '_onTimeRangeModified',
        time_range_removed: '_onTimeRangeRemoved',
    },
    defaults: _.extend({}, Widget.prototype.defaults, {
        hidden: false,
        disable_custom_filters: false,
        disable_groupby: false,
        disable_favorites: false,
        disable_filters: false,
        disableTimeRangeMenu: true,
    }),
    template: "SearchView",

    /**
     * @constructs SearchView
     * @extends View
     *
     * @param parent
     * @param dataset
     * @param fvg
     * @param {Object} [options]
     * @param {Boolean} [options.hidden=false] hide the search view
     * @param {Boolean} [options.disable_custom_filters=false] do not load custom filters from ir.filters
     */
    init: function (parent, dataset, fvg, options) {
        this._super.apply(this, arguments);
        this.options = options;
        this.dataset = dataset;
        this.fields_view = this._processFieldsView(_.clone(fvg));

        this.fields = this.fields_view.fields;
        this.query = undefined;
        this.title = this.options.action && this.options.action.name;
        this.action = this.options.action || {};
        this.search_fields = [];

        this.hasFavorites = false;

        this.noDateFields = true;
        var field;
        for (var key in this.fields) {
            field = this.fields[key];
            if (_.contains(['date', 'datetime'], field.type) && field.sortable) {
                this.noDateFields = false;
                break;
            }
        }
        this.activeItemIds = {
            groupByCategory: [],
            filterCategory: []
        };
        this.groupsMapping = [];
        this.groupbysMapping = [];
        this.filtersMapping = [];
        this.intervalMapping = [];
        this.periodMapping = [];

        this.filters = [];
        this.groupbys = [];
        this.timeRanges = options.action && options.action.context ?
            options.action.context.time_ranges : undefined;
        var visibleSearchMenu = this.call('local_storage', 'getItem', 'visible_search_menu');
        this.visible_filters = (visibleSearchMenu !== false);
        this.input_subviews = []; // for user input in searchbar
        this.search_defaults = this.options.search_defaults || {};
        this.headless = this.options.hidden &&  _.isEmpty(this.search_defaults);
        this.$buttons = this.options.$buttons;

        this.filters_menu = undefined;
        this.groupby_menu = undefined;
        this.favorite_menu = undefined;
    },
    willStart: function () {
        var self = this;
        var def;
        if (!this.options.disable_favorites) {
            def = this.loadFilters(this.dataset, this.action.id).then(function (filters) {
                self.favorite_filters = filters;
            });
        }
        return $.when(this._super(), def);
    },
    start: function () {
        var self= this;
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
        var def;
        this.prepare_search_inputs();
        var $buttons = this._getButtonsElement();
        if ($buttons) {
            if (!this.options.disable_favorites) {
                this.favorite_menu = new FavoriteMenu(this, this.query, this.dataset.model, this.action, this.favorite_filters);
                def = this.favorite_menu.appendTo($buttons);
            }
        }
        return $.when(def)
            .then(this.set_default_filters.bind(this))
            .then(function ()  {
                var menu_defs = [];
                self.timeRangeMenu = self._createTimeRangeMenu();
                menu_defs.push(self.timeRangeMenu.prependTo($buttons));
                self.timeRangeMenu.do_hide();
                self.displayedTimeRangeMenu = self.options.disableTimeRangeMenu !== undefined &&
                    !self.options.disableTimeRangeMenu;
                self.displayTimeRangeMenu(self.displayedTimeRangeMenu);
                if (!self.options.disable_groupby) {
                    self.groupby_menu = self._createGroupByMenu();
                    menu_defs.push(self.groupby_menu.prependTo($buttons));
                }
                if (!self.options.disable_filters) {
                    self.filters_menu = self._createFiltersMenu();
                    menu_defs.push(self.filters_menu.prependTo($buttons));
                }
                return $.when.apply($, menu_defs);
            });
    },
    /*
     *
     * @param {boolean}
     */
    displayTimeRangeMenu: function (b) {
        if (!b || this.noDateFields) {
            this.timeRangeMenu.do_hide();
        } else {
            this.timeRangeMenu.do_show();
        }
    },
    on_attach_callback: function () {
        this._focusInput();
    },
    get_title: function () {
        return this.title;
    },
    set_default_filters: function () {
        var self = this,
            default_custom_filter = this.$buttons && this.favorite_menu && this.favorite_menu.get_default_filter();
        if (!self.options.disable_custom_filters && default_custom_filter) {
            this.hasFavorites = true;
            return this.favorite_menu.toggle_filter(default_custom_filter, true);
        }
        if (!_.isEmpty(this.search_defaults) || this.timeRanges) {
            var inputs = this.search_fields.concat(this.filters, this.groupbys);
            var search_defaults = _.invoke(inputs, 'facet_for_defaults', this.search_defaults);
            var defaultTimeRange = this._searchDefaultTimeRange();
            search_defaults.push(defaultTimeRange);
            return $.when.apply(null, search_defaults).then(function () {
                var facets = _.compact(arguments);
                self.query.reset(facets, {preventSearch: true});
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
        this.trigger_up('search', search);
    },
    /**
     * @param {boolean} noDomainEvaluation determines if domain are evaluated or not.
     *                   By default, domains are evaluated.
     *
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
    build_search_data: function (noDomainEvaluation) {
        var domains = [], contexts = [], groupbys = [];
        noDomainEvaluation = noDomainEvaluation || false;
        this.query.each(function (facet) {
            // field is actually a FilterGroup!
            var field = facet.get('field');
            var domain = field.get_domain(facet, noDomainEvaluation);
            if (domain) {
                domains.push(domain);
            }
            var context = field.get_context(facet, noDomainEvaluation);
            if (context) {
                contexts.push(context);
            }
            var group_by = field.get_groupby(facet);
            if (group_by) {
                groupbys.push.apply(groupbys, group_by);
            }
        });
        var intervalMappingNormalized = {};
        _.each(this.intervalMapping, function (couple) {
            var fieldName = couple.groupby.fieldName;
            var interval = couple.interval;
            intervalMappingNormalized[fieldName] = interval;
        });
        return {
            domains: domains,
            contexts: contexts,
            groupbys: groupbys,
            intervalMapping: intervalMappingNormalized,
        };
    },
    toggle_visibility: function (is_visible) {
        this.do_toggle(!this.headless && is_visible);
        if (this.$buttons) {
            this.$buttons.toggle(!this.headless && is_visible && this.visible_filters);
        }
        this._focusInput();
    },
    /**
     * puts the focus on the search input
     */
    _focusInput: function () {
        if (!config.device.touch && config.device.size_class >= config.device.SIZES.MD) {
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
        this.autocomplete.appendTo(this.$('.o_searchview_input_container'));
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
        var facet = ui.item.facet;
        e.preventDefault();
        if(facet && facet.values && facet.values.length && String(facet.values[0].value).trim() !== "") {
            this.query.add(facet);
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
     */
    renderFacets: function () {
        var self = this;
        var started = [];
        _.invoke(this.input_subviews, 'destroy');
        this.input_subviews = [];

        var activeItemIds = {
            groupByCategory: [],
            filterCategory: [],
        };
        var timeRangeMenuIsActive;
        this.query.each(function (facet) {
            var values = facet.get('values');
            if (facet.attributes.cat === "groupByCategory") {
                activeItemIds.groupByCategory = activeItemIds.groupByCategory.concat(
                    _.uniq(
                        values.reduce(
                            function (acc, value) {
                                var groupby = value.value;
                                var description = _.findWhere(self.groupbysMapping, {groupby: groupby});
                                if (description) {
                                    acc.push(description.groupbyId);
                                }
                                return acc;
                            },
                            []
                        )
                    )
                );
            }
            if (facet.attributes.cat === "filterCategory") {
                activeItemIds.filterCategory = activeItemIds.filterCategory.concat(
                    _.uniq(
                        values.reduce(
                            function (acc, value) {
                                var filter = value.value;
                                var description = _.findWhere(self.filtersMapping, {filter: filter});
                                if (description) {
                                    acc.push(description.filterId);
                                }
                                return acc;
                            },
                            []
                        )
                    )
                );
            }
            if (facet.attributes.cat === "timeRangeCategory") {
                timeRangeMenuIsActive = true;
            }
            var f = new FacetView(this, facet, this.intervalMapping, this.periodMapping);
            started.push(f.appendTo(self.$('.o_searchview_input_container')));
            self.input_subviews.push(f);
        }, this);

        var i = new InputView(this);
        started.push(i.appendTo(self.$('.o_searchview_input_container')));
        self.input_subviews.push(i);
        _.each(this.input_subviews, function (childView) {
            childView.on('focused', self, self.proxy('childFocused'));
            childView.on('blurred', self, self.proxy('childBlurred'));
        });

        $.when.apply(null, started).then(function () {
            if (!config.device.isMobile) {
                // in mobile mode, we would rathor not focusing manually the
                // input, because it opens up the integrated keyboard, which is
                // not what you expect when you just selected a filter.
                _.last(self.input_subviews).$el.focus();
            }
            if (self.groupby_menu) {
                self.groupby_menu.updateItemsStatus(activeItemIds.groupByCategory);
            }
            if (self.filters_menu) {
                self.filters_menu.updateItemsStatus(activeItemIds.filterCategory);            }
            if (self.displayedTimeRangeMenu && !timeRangeMenuIsActive) {
                self.timeRangeMenu.deactivate();
            }
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
                    var context = pyUtils.eval('context', item.attrs.context);
                    if (context.group_by) {
                        category = 'group_by';
                        item.attrs.fieldName = context.group_by.split(':')[0];
                        item.attrs.isDate = _.contains(['date', 'datetime'], self.fields[item.attrs.fieldName].type);
                        item.attrs.defaultInterval = context.group_by.split(':')[1];
                    }
                } catch (e) {}
            }
            if (item.attrs.date) {
                item.attrs.default_period = item.attrs.default_period || DEFAULT_PERIOD;
                item.attrs.type = self.fields[item.attrs.date].type;
            }
            item.attrs.isPeriod = !!item.attrs.date;
            return {
                item: item,
                category: category,
            };
        }
        var current_group = [],
            current_category = 'filters',
            categories = {filters: this.filters, group_by: this.groupbys, timeRanges: this.timeRanges};

        _.each(filters.concat({category:'filters', item: 'separator'}), function (filter) {
            if (filter.item.tag === 'filter' && filter.category === current_category) {
                return current_group.push(new search_inputs.Filter(filter.item, self));
            }
            if (current_group.length) {
                var group = new search_inputs.FilterGroup(current_group, self, self.intervalMapping, self.periodMapping);
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
                var Obj = core.search_widgets_registry.getAny([attrs.widget, field.type]);
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

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Updates the domain of the search view by adding and/or removing filters.
     *
     * @todo: the way it is done could be improved, but the actual state of the
     * searchview doesn't allow to do much better.

     * @param {Array<Object>} newFilters list of filters to add, described by
     *   objects with keys domain (the domain as an Array), and help (the text
     *   to display in the facet)
     * @param {Array<Object>} filtersToRemove list of filters to remove
     *   (previously added ones)
     * @returns {Array<Object>} list of added filters (to pass as filtersToRemove
     *   for a further call to this function)
     */
    updateFilters: function (newFilters, filtersToRemove) {
        var self = this;
        var addedFilters = _.map(newFilters, function (filter) {
            var domain = filter.domain;
            if (domain instanceof Array) {
                domain =  Domain.prototype.arrayToString(domain);
            }
            filter = {
                attrs: {domain: domain, help: filter.help},
            };
            var filterWidget = new search_inputs.Filter(filter);
            var filterGroup = new search_inputs.FilterGroup([filterWidget], self, self.intervalMapping, self.periodMapping);
            var facet = filterGroup.make_facet([filterGroup.make_value(filter)]);
            self.query.add([facet], {silent: true});

            return _.last(self.query.models);
        });

        _.each(filtersToRemove, function (filter) {
            self.query.remove(filter, {silent: true});
        });

        this.query.trigger('reset');

        return addedFilters;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------


    /**
     * Will return $element where Filters, Group By and Favorite buttons are
     * going to be pushed. This method is overriden by the mobile search view
     * to add these buttons somewhere else in the dom.
     *
     * @private
     * @returns {jQueryElement}
     */
    _getButtonsElement: function () {
        return this.$buttons;
    },
    /**
     * Create a groupby menu.  Note that this method has a side effect: it
     * builds a mapping from a filter name to a 'search filter'.
     *
     * @private
     * @returns {Widget} the processed fieldsView
     */
    _createFiltersMenu: function () {
        var self = this;
        var filters = [];

        this.filters.forEach(function (group) {
            var groupId = _.uniqueId('__group__');
            group.filters.forEach(function (filter) {
                if (!filter.attrs.invisible) {
                    var filterId = _.uniqueId('__filter__');
                    var isPeriod = filter.attrs.isPeriod;
                    var defaultPeriod = filter.attrs.default_period;
                    var isActive = !self.hasFavorites && !!self.search_defaults[filter.attrs.name];
                    filters.push({
                        itemId: filterId,
                        description: filter.attrs.string || filter.attrs.help ||
                            filter.attrs.name || filter.attrs.domain || 'Ω',
                        domain: filter.attrs.domain,
                        fieldName: filter.attrs.date,
                        isPeriod: isPeriod,
                        defaultOptionId: defaultPeriod,
                        isActive: isActive,
                        groupId: groupId,
                    });
                    self.filtersMapping.push({filterId: filterId, filter: filter, groupId: groupId});
                    if (isPeriod) {
                        self.periodMapping.push({filter: filter, period: defaultPeriod, type: filter.attrs.type});
                    }
                }
            });
            self.groupsMapping.push({groupId: groupId, group: group, category: 'Filters'});
        });

        return new FiltersMenu(self, filters, self.fields);
    },

    /**
     * Create a groupby menu.  Note that this method has a side effect: it
     * builds a mapping from a filter name to a 'search filter'.
     *
     * @private
     * @returns {Widget} the processed fieldsView
     */
    _createGroupByMenu: function () {
        var self = this;
        var groupbys = [];

        this.groupbys.forEach(function (group) {
            var groupId = _.uniqueId('__group__');
            group.filters.forEach(function (groupby) {
                if (!groupby.attrs.invisible) {
                    var groupbyId = _.uniqueId('__groupby__');
                    var fieldName = groupby.attrs.fieldName;
                    var isDate = groupby.attrs.isDate;
                    var defaultInterval = groupby.attrs.defaultInterval || DEFAULT_INTERVAL;
                    var isActive = !self.hasFavorites && !!self.search_defaults[groupby.attrs.name];
                    groupbys.push({
                        itemId: groupbyId,
                        description: groupby.attrs.string || groupby.attrs.help || groupby.attrs.name
                            || groupby.attrs.fieldName || 'Ω',
                        isDate: isDate,
                        fieldName: fieldName,
                        defaultOptionId: defaultInterval,
                        isActive: isActive,
                        groupId: groupId,
                    });
                    if (isDate) {
                        self.intervalMapping.push({groupby: groupby, interval: defaultInterval});
                    }
                    self.groupbysMapping.push({groupbyId: groupbyId, groupby: groupby, groupId: groupId});
                }
            });
            self.groupsMapping.push({groupId: groupId, group: group, category: 'Group By'});
            group.updateIntervalMapping(self.intervalMapping);
        });
        return new GroupByMenu(this, groupbys, this.fields);
    },
    /**
     * Create a time range menu.
     *
     * @private
     * @returns {Widget} the range menu
     */
     _createTimeRangeMenu: function () {
        return new TimeRangeMenu(this, this.fields, this.timeRanges);
     },
    /**
     * Processes a fieldsView in place. In particular, parses its arch.
     *
     * @todo: this function is also defined in AbstractView ; this code
     * duplication could be removed once the SearchView will be rewritten.
     * @private
     * @param {Object} fv
     * @param {string} fv.arch
     * @returns {Object} the processed fieldsView
     */
    _processFieldsView: function (fv) {
        var doc = $.parseXML(fv.arch).documentElement;
        fv.arch = utils.xml_to_json(doc, true);
        return fv;
    },
    /**
     * @returns {Deferred}
     */
    _searchDefaultTimeRange: function () {
        if (this.timeRanges) {
            var timeRange = "[]";
            var timeRangeDescription;
            var comparisonTimeRange = "[]";
            var comparisonTimeRangeDescription;

            var dateField = {
                name: this.timeRanges.field,
                type: this.fields[this.timeRanges.field].type,
                description: this.fields[this.timeRanges.field].string,
            };

            timeRange = Domain.prototype.constructDomain(
                dateField.name,
                this.timeRanges.range,
                dateField.type
            );
            timeRangeDescription = _.findWhere(
                PeriodOptions,
                {optionId: this.timeRanges.range}
            ).description;

            if (this.timeRanges.comparison_range) {
                comparisonTimeRange = Domain.prototype.constructDomain(
                    dateField.name,
                    this.timeRanges.range,
                    dateField.type,
                    null,
                    this.timeRanges.comparison_range
                );
                comparisonTimeRangeDescription = _.findWhere(
                    ComparisonOptions,
                    {optionId: this.timeRanges.comparison_range}
                ).description;
            }

            return $.when({
                cat: 'timeRangeCategory',
                category: _t("Time Range"),
                icon: 'fa fa-calendar',
                field: {
                    get_context: function (facet, noDomainEvaluation) {
                        if (!noDomainEvaluation) {
                            timeRange = Domain.prototype.stringToArray(timeRange);
                            comparisonTimeRange = Domain.prototype.stringToArray(comparisonTimeRange);
                        }
                        return {
                            timeRangeMenuData: {
                                timeRange: timeRange,
                                timeRangeDescription: timeRangeDescription,
                                comparisonTimeRange: comparisonTimeRange,
                                comparisonTimeRangeDescription: comparisonTimeRangeDescription,
                            }
                        };
                },
                    get_groupby: function () {},
                    get_domain: function () {}
                },
                isRange: true,
                values: [{
                    label: dateField.description + ': ' + timeRangeDescription +
                        (
                            comparisonTimeRangeDescription ?
                                (' / ' + comparisonTimeRangeDescription) :
                                ''
                        ),
                    value: null,
                }],
            });
        } else {
            return $.when();
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     *
     * this function is called in response to an event 'on_item_toggled'.
     * this kind of event is triggered by the filters menu or the groupby menu
     * when a user has clicked on a item (a filter or a groupby).
     * The query is modified accordingly to the new state (active or not) of that item
     *
     * @private
     * @param {OdooEvent} event
     */
    _onItemToggled: function (event) {
        var group;
        if (event.data.category === 'groupByCategory') {
            var groupby = _.findWhere(this.groupbysMapping, {groupbyId: event.data.itemId}).groupby;
            group = _.findWhere(this.groupsMapping, {groupId: event.data.groupId}).group;
            if (event.data.optionId) {
                var interval = event.data.optionId;
                _.findWhere(this.intervalMapping, {groupby: groupby}).interval = interval;
                group.updateIntervalMapping(this.intervalMapping);
            }
            group.toggle(groupby);
        }
        if (event.data.category === 'filterCategory') {
            var filter = _.findWhere(this.filtersMapping, {filterId: event.data.itemId}).filter;
            group = _.findWhere(this.groupsMapping, {groupId: event.data.groupId}).group;
            if (event.data.optionId) {
                var period = event.data.optionId;
                _.findWhere(this.periodMapping, {filter: filter}).period = period;
                group.updatePeriodMapping(this.periodMapping);
            }
            group.toggle(filter);
        }
    },
    /**
     * this function is called when a new groupby has been added to the groupby menu
     * via the 'Add Custom Groupby' submenu. The query is modified with the new groupby
     * added to it as active. The communication betwenn the groupby menu and the search view
     * is maintained by properly updating the mappings.
     * @private
     * @param {OdooEvent} event
     */
    _onNewGroupby: function (event) {
        var isDate = event.data.isDate;
        var attrs = {
            context:"{'group_by':'" + event.data.fieldName + "''}",
            name: event.data.description,
            fieldName: event.data.fieldName,
            isDate: isDate,
        };
        var groupby = new search_inputs.Filter({attrs: attrs}, this);
        if (event.data.optionId) {
            var interval = event.data.optionId;
            this.intervalMapping.push({groupby: groupby, interval: interval});
        }
        var group = new search_inputs.FilterGroup([groupby], this, this.intervalMapping, this.periodMapping);
        this.groupbysMapping.push({
            groupbyId: event.data.itemId,
            groupby: groupby,
            groupId: event.data.groupId,
        });
        this.groupsMapping.push({
            groupId: event.data.groupId,
            group: group,
            category: 'Group By',
        });
        group.toggle(groupby);
    },
    /**
     * this function is called when a new filter has been added to the filters menu
     * via the 'Add Custom Filter' submenu. The query is modified with the new filter
     * added to it as active. The communication betwenn the filters menu and the search view
     * is maintained by properly updating the mappings.
     * @private
     * @param {OdooEvent} event
     */
    _onNewFilters: function (event) {
        var self= this;
        var filter;
        var filters = [];
        var groupId;

        _.each(event.data, function (filterDescription) {
            filter = new search_inputs.Filter(filterDescription.filter, this);
            filters.push(filter);
            self.filtersMapping.push({
                filterId: filterDescription.itemId,
                filter: filter,
                groupId: filterDescription.groupId,
            });
            // filters belong to the same group
            if (!groupId) {
                groupId = filterDescription.groupId;
            }
        });
        var group = new search_inputs.FilterGroup(filters, this, this.intervalMapping, this.periodMapping);
        filters.forEach(function (filter) {
            group.toggle(filter, {silent: true});
        });
        this.groupsMapping.push({
            groupId: groupId,
            group: group,
            category: 'Filters',
        });
        this.query.trigger('reset');
    },
    /**
     * this function is called when the option related to an item (filter or groupby) has been
     * changed by the user. The query is modified appropriately.
     *
     * @private
     * @param {OdooEvent} event
     */
    _onItemOptionChanged: function (event) {
        var group;
        if (event.data.category === 'groupByCategory') {
            var groupby = _.findWhere(this.groupbysMapping, {groupbyId: event.data.itemId}).groupby;
            var interval = event.data.optionId;
            _.findWhere(this.intervalMapping, {groupby: groupby}).interval = interval;
            group = _.findWhere(this.groupsMapping, {groupId: event.data.groupId}).group;
            group.updateIntervalMapping(this.intervalMapping);
            this.query.trigger('reset');
        }
        if (event.data.category === 'filterCategory') {
            var filter = _.findWhere(this.filtersMapping, {filterId: event.data.itemId}).filter;
            var period = event.data.optionId;
            _.findWhere(this.periodMapping, {filter: filter}).period = period;
            group = _.findWhere(this.groupsMapping, {groupId: event.data.groupId}).group;
            group.updatePeriodMapping(this.periodMapping);
            this.query.trigger('reset');
        }
    },
    /*
     * @private
     * @param {JQueryEvent} event
     */
    _onTimeRangeModified: function () {
        var facet = this.timeRangeMenu.facetFor();
        var current = this.query.find(function (facet) {
            return facet.get('cat') === 'timeRangeCategory';
        });
        if (current) {
            this.query.remove(current, {silent: true});
        }
        this.query.add(facet);
    },
    /*
     * @private
     */
    _onTimeRangeRemoved: function () {
        var current = this.query.find(function (facet) {
            return facet.get('cat') === 'timeRangeCategory';
        });
        if (current) {
            this.query.remove(current);
        }
    },
});

_.extend(SearchView, {
    SearchQuery: SearchQuery,
    Facet: Facet,
});

return SearchView;

});
