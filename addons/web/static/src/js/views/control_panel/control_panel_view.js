odoo.define('web.ControlPanelView', function (require) {
"use strict";

var ControlPanelController = require('web.ControlPanelController');
var ControlPanelModel = require('web.ControlPanelModel');
var ControlPanelRenderer = require('web.ControlPanelRenderer');
var controlPanelViewParameters = require('web.controlPanelViewParameters');
var mvc = require('web.mvc');
var pyUtils = require('web.py_utils');
var viewUtils = require('web.viewUtils');
var Domain = require('web.Domain');

var DEFAULT_INTERVAL = controlPanelViewParameters.DEFAULT_INTERVAL;
var DEFAULT_PERIOD = controlPanelViewParameters.DEFAULT_PERIOD;
var INTERVAL_OPTIONS = controlPanelViewParameters.INTERVAL_OPTIONS;
var PERIOD_OPTIONS = controlPanelViewParameters.PERIOD_OPTIONS;
const OPTION_GENERATORS = controlPanelViewParameters.OPTION_GENERATORS;

var Factory = mvc.Factory;

var ControlPanelView = Factory.extend({
    config: _.extend({}, Factory.prototype.config, {
        Controller: ControlPanelController,
        Model: ControlPanelModel,
        Renderer: ControlPanelRenderer,
    }),

    /**
     * @override
     * @param {Object} [params={}]
     * @param {Object} [params.action={}]
     * @param {Object} [params.context={}]
     * @param {string} [params.domain=[]]
     * @param {string} [params.modelName]
     * @param {string[]} [params.searchMenuTypes=[]]
     *   determines search menus displayed.
     * @param {Object} [params.state] used to determine the control panel model
     *   essential content at load. For instance, state can be the state of an
     *   other control panel model that we want to use.
     * @param {string} [params.title] the name of the action, to display in the
     *   breadcrumb
     * @param {string} [params.template] the QWeb template to render
     * @param {Object} [params.viewInfo={arch: '<search/>', fields: {}}] a
     *   search fieldsview
     * @param {string} [params.viewInfo.arch]
     * @param {boolean} [params.withBreadcrumbs=true] if set to false,
     *   breadcrumbs won't be rendered
     * @param {boolean} [params.withSearchBar=true] if set to false, no default
     *   search bar will be rendered
     * @param {Object[]} [params.dynamicFilters=[]] filters to add to the
     *   search (in addition to those described in the arch), each filter being
     *   an object with keys 'description' (what is displayed in the searchbar)
     *   and 'domain'
     */
    init: function (params) {
        var self = this;
        this._super();
        params = params || {};
        var viewInfo = params.viewInfo || {arch: '<search/>', fields: {}};
        var context = _.extend({}, params.context);
        var domain = params.domain || [];
        var action = params.action || {};

        this.searchDefaults = {};
        Object.keys(context).forEach(function (key) {
            var match = /^search_default_(.*)$/.exec(key);
            if (match) {
                self.searchDefaults[match[1]] = context[key];
                delete context[key];
            }
        });

        this.arch = viewUtils.parseArch(viewInfo.arch);
        this.fields = viewInfo.fields;

        this.referenceMoment = moment();
        this.optionGenerators = OPTION_GENERATORS.map(o => {
            const description = o.description ?
                                    o.description.toString () :
                                    this.referenceMoment.clone().set(o.setParam).add(o.addParam).format(o.format);
            return _.extend({}, o, {description:  description});
        });
        PERIOD_OPTIONS = PERIOD_OPTIONS.map(option =>
            _.extend({}, option, {description: option.description.toString()})
        );
        INTERVAL_OPTIONS = INTERVAL_OPTIONS.map(option =>
            _.extend({}, option, {description: option.description.toString()})
        );

        this.controllerParams.modelName = params.modelName;

        this.modelParams.context = context;
        this.modelParams.domain = domain;
        this.modelParams.modelName = params.modelName;
        this.modelParams.actionId = action.id;
        this.modelParams.fields = this.fields;

        this.rendererParams.action = action;
        this.rendererParams.breadcrumbs = params.breadcrumbs;
        this.rendererParams.context = context;
        this.rendererParams.searchMenuTypes = params.searchMenuTypes || [];
        this.rendererParams.template = params.template;
        this.rendererParams.title = params.title;
        this.rendererParams.withBreadcrumbs = params.withBreadcrumbs !== false;
        this.rendererParams.withSearchBar = 'withSearchBar' in params ? params.withSearchBar : true;

        this.loadParams.withSearchBar = 'withSearchBar' in params ? params.withSearchBar : true;
        this.loadParams.searchMenuTypes = params.searchMenuTypes || [];
        this.loadParams.activateDefaultFavorite = params.activateDefaultFavorite;
        if (this.loadParams.withSearchBar) {
            if (params.state) {
                this.loadParams.initialState = params.state;
            } else {
                // groups are determined in _parseSearchArch
                this.loadParams.groups = [];
                this.loadParams.timeRanges = context.time_ranges;
                this._parseSearchArch(this.arch);
            }
        }

        // add a filter group with the dynamic filters, if any
        if (params.dynamicFilters && params.dynamicFilters.length) {
            var dynamicFiltersGroup = params.dynamicFilters.map(function (filter) {
                return {
                    description: filter.description,
                    domain: JSON.stringify(filter.domain),
                    isDefault: true,
                    type: 'filter',
                };
            });
            this.loadParams.groups.unshift(dynamicFiltersGroup);
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Object} child parsed arch node
     * @returns {Object}
     */
    _evalArchChild: function (child) {
        if (child.attrs.context) {
            try {
                var context = pyUtils.eval('context', child.attrs.context);
                if (context.group_by) {
                    // let us extract basic data since we just evaluated context
                    // and use a correct tag!
                    child.tag = 'groupBy';
                    child.attrs.fieldName = context.group_by.split(':')[0];
                    child.attrs.defaultInterval = context.group_by.split(':')[1];
                }
            } catch (e) {}
        }
        return child;
    },
    /**
     * @private
     * @param {Object} filter
     * @param {Object} attrs
     */
    _extractAttributes: function (filter, attrs) {
        filter.isDefault = this.searchDefaults[attrs.name] ? true : false;
        filter.description = attrs.string ||
                                attrs.help ||
                                attrs.name ||
                                attrs.domain ||
                                'Ω';
        if (attrs.invisible) {
            filter.invisible = true;
        }
        if (filter.type === 'filter') {
            if (filter.isDefault) {
                filter.defaultRank = -5;
            }
            filter.domain = attrs.domain;
            filter.context = pyUtils.eval('context', attrs.context);
            if (attrs.date) {
                filter.fieldName = attrs.date;
                filter.fieldType = this.fields[attrs.date].type;
                filter.hasOptions = true;
                filter.options = this.optionGenerators;
                filter.defaultOptionId = attrs.default_period ||
                                            DEFAULT_PERIOD;
                filter.currentOptionIds = new Set();
                filter.basicDomains = this._getDateFilterBasicDomains(filter);
            }
        } else if (filter.type === 'groupBy') {
            if (filter.isDefault) {
                const val = this.searchDefaults[attrs.name];
                filter.defaultRank = typeof val === 'number' ? val : 100;
            }
            filter.fieldName = attrs.fieldName;
            filter.fieldType = this.fields[attrs.fieldName].type;
            if (_.contains(['date', 'datetime'], filter.fieldType)) {
                filter.hasOptions = true;
                filter.options = INTERVAL_OPTIONS;
                filter.defaultOptionId = attrs.defaultInterval ||
                                            DEFAULT_INTERVAL;
                filter.currentOptionIds = new Set();
            }
        } else if (filter.type === 'field') {
            if (filter.isDefault) {
                filter.defaultRank = -10;
            }
            var field = this.fields[attrs.name];
            filter.attrs = attrs;
            filter.autoCompleteValues = [];
            if (filter.isDefault) {
                // on field, default can be used with a value
                filter.defaultValue = this.searchDefaults[filter.attrs.name];
            }
            if (!attrs.string) {
                attrs.string = field.string;
            }
        }
    },
    /**
     * Constructs an object containing various domains based on this.referenceMoment and
     * the field associated with the provided date filter.
     *
     * @private
     * @param {Object} filter
     * @returns {Object}
     */
    _getDateFilterBasicDomains: function (filter) {
        const _constructBasicDomain = (y, o) => {
            const addParam = _.extend({}, y.addParam, o ? o.addParam : {});
            const setParam = _.extend({}, y.setParam, o ? o.setParam : {});
            const granularity = o ? o.granularity : y.granularity;
            const date = this.referenceMoment.clone().set(setParam).add(addParam);
            let leftBound = date.clone().startOf(granularity).locale('en');
            let rightBound = date.clone().endOf(granularity).locale('en');

            if (filter.fieldType === 'date') {
                leftBound = leftBound.format("YYYY-MM-DD");
                rightBound = rightBound.format("YYYY-MM-DD");
            } else {
                leftBound = leftBound.utc().format("YYYY-MM-DD HH:mm:ss");
                rightBound = rightBound.utc().format("YYYY-MM-DD HH:mm:ss");
            }
            const domain = Domain.prototype.arrayToString([
                '&',
                [filter.fieldName, ">=", leftBound],
                [filter.fieldName, "<=", rightBound]
            ]);

            let description;
            if (o) {
                description = o.description + " " + y.description;
            } else {
                description = y.description;
            }

            return { domain, description };
        };

        const domains = {};
        this.optionGenerators.filter(y => y.groupId === 2).forEach(y => {
            domains[y.optionId] = _constructBasicDomain(y);
            this.optionGenerators.filter(y => y.groupId === 1).forEach(o => {
                domains[y.optionId + "__" + o.optionId] = _constructBasicDomain(y, o);
            });
        });
        return domains;
    },
    /**
     * Parse the arch of a 'search' view.
     *
     * @private
     * @param {Object} arch arch with root node <search>
     */
    _parseSearchArch: function (arch) {
        var self = this;
        // a searchview arch may contain a 'searchpanel' node, but this isn't
        // the concern of the ControlPanelView (the SearchPanel will handle it).
        // Ideally, this code should whitelist the tags to take into account
        // instead of blacklisting the others, but with the current (messy)
        // structure of a searchview arch, it's way simpler to do it that way.
        var children = arch.children.filter(function (child) {
            return child.tag !== 'searchpanel';
        });
        var preFilters = _.flatten(children.map(function (child) {
            return child.tag !== 'group' ?
                    self._evalArchChild(child) :
                    child.children.map(self._evalArchChild);
        }));
        preFilters.push({tag: 'separator'});

        var filter;
        var currentTag;
        var currentGroup = [];
        var groupOfGroupBys = [];
        var groupNumber = 1;

        _.each(preFilters, function (preFilter) {
            if (preFilter.tag !== currentTag || _.contains(['separator', 'field'], preFilter.tag)) {
                if (currentGroup.length) {
                    if (currentTag === 'groupBy') {
                        groupOfGroupBys = groupOfGroupBys.concat(currentGroup);
                    } else {
                        self.loadParams.groups.push(currentGroup);
                    }
                }
                currentTag = preFilter.tag;
                currentGroup = [];
                groupNumber++;
            }
            if (preFilter.tag !== 'separator') {
                filter = {
                    type: preFilter.tag,
                    // we need to codify here what we want to keep from attrs
                    // and how, for now I put everything.
                    // In some sence, some filter are active (totally determined, given)
                    // and others are passive (require input(s) to become determined)
                    // What is the right place to process the attrs?
                };
                if (filter.type === 'filter' || filter.type === 'groupBy') {
                    filter.groupNumber = groupNumber;
                }
                self._extractAttributes(filter, preFilter.attrs);
                currentGroup.push(filter);
            }
        });
        if (groupOfGroupBys.length) {
            this.loadParams.groups.push(groupOfGroupBys);
        }
    },
});

return ControlPanelView;

});
