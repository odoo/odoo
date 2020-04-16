odoo.define('web.AbstractView', function (require) {
"use strict";

/**
 * This is the base class inherited by all (JS) views. Odoo JS views are the
 * widgets used to display information in the main area of the web client
 * (note: the search view is not a "JS view" in that sense).
 *
 * The abstract view role is to take a set of fields, an arch (the xml
 * describing the view in db), and some params, and then, to create a
 * controller, a renderer and a model.  This is the classical MVC pattern, but
 * the word 'view' has historical significance in Odoo code, so we replaced the
 * V in MVC by the 'renderer' word.
 *
 * JS views are supposed to be used like this:
 * 1. instantiate a view with some arch, fields and params
 * 2. call the getController method on the view instance. This returns a
 *    controller (with a model and a renderer as sub widgets)
 * 3. append the controller somewhere
 *
 * Note that once a controller has been instantiated, the view class is no
 * longer useful (unless you want to create another controller), and will be
 * in most case discarded.
 */

var AbstractModel = require('web.AbstractModel');
var AbstractRenderer = require('web.AbstractRenderer');
var AbstractController = require('web.AbstractController');
const ControlPanelModel = require('web.ControlPanelModel');
var mvc = require('web.mvc');
var SearchPanel = require('web.SearchPanel');
var viewUtils = require('web.viewUtils');

const { Component } = owl;

var Factory = mvc.Factory;

var AbstractView = Factory.extend({
    // name displayed in view switchers
    display_name: '',
    // indicates whether or not the view is mobile-friendly
    mobile_friendly: false,
    // icon is the font-awesome icon to display in the view switcher
    icon: 'fa-question',
    // multi_record is used to distinguish views displaying a single record
    // (e.g. FormView) from those that display several records (e.g. ListView)
    multi_record: true,
    // viewType is the type of the view, like 'form', 'kanban', 'list'...
    viewType: undefined,
    // determines if a search bar is available
    withSearchBar: true,
    // determines the search menus available and their orders
    searchMenuTypes: ['filter', 'groupBy', 'favorite'],
    // determines if a control panel should be instantiated
    withControlPanel: true,
    // determines if a search panel could be instantiated
    withSearchPanel: true,
    // determines the MVC components to use
    config: _.extend({}, Factory.prototype.config, {
        Model: AbstractModel,
        Renderer: AbstractRenderer,
        Controller: AbstractController,
        SearchPanel: SearchPanel,
    }),

    /**
     * The constructor function is supposed to set 3 variables: rendererParams,
     * controllerParams and loadParams.  These values will be used to initialize
     * the model, renderer and controllers.
     *
     * @constructs AbstractView
     *
     * @param {Object} viewInfo
     * @param {Object|string} viewInfo.arch
     * @param {Object} viewInfo.fields
     * @param {Object} viewInfo.fieldsInfo
     * @param {Object} params
     * @param {string} [params.modelName]
     * @param {Object} [params.action={}]
     * @param {Object} [params.context={}]
     * @param {string} [params.controllerID]
     * @param {number} [params.count]
     * @param {number} [params.currentId]
     * @param {Object} [params.controllerState]
     * @param {string} [params.displayName]
     * @param {Array[]} [params.domain=[]]
     * @param {Object[]} [params.dynamicFilters] transmitted to the
     *   ControlPanel
     * @param {number[]} [params.ids]
     * @param {boolean} [params.isEmbedded=false]
     * @param {Object} [params.searchQuery={}]
     * @param {Object} [params.searchQuery.context={}]
     * @param {Array[]} [params.searchQuery.domain=[]]
     * @param {string[]} [params.searchQuery.groupBy=[]]
     * @param {Object} [params.userContext={}]
     * @param {boolean} [params.withControlPanel=AbstractView.prototype.withControlPanel]
     * @param {boolean} [params.withSearchPanel=AbstractView.prototype.withSearchPanel]
     */
    init: function (viewInfo, params) {
        this._super.apply(this, arguments);

        var action = params.action || {};
        params = _.defaults(params, this._extractParamsFromAction(action));

        // in general, the fieldsView has to be processed by the View (e.g. the
        // arch is a string that needs to be parsed) ; the only exception is for
        // inline form views inside form views, as they are processed alongside
        // the main view, but they are opened in a FormViewDialog which
        // instantiates another FormView (unlike kanban or list subviews for
        // which only a Renderer is instantiated)
        if (typeof viewInfo.arch === 'string') {
            this.fieldsView = this._processFieldsView(viewInfo);
        } else {
            this.fieldsView = viewInfo;
        }
        this.arch = this.fieldsView.arch;
        this.fields = this.fieldsView.viewFields;
        this.userContext = params.userContext || {};
        this.withControlPanel = this.withControlPanel && params.withControlPanel;
        const searchPanelDisabled = 'search_panel' in params.context && !params.search_panel;
        this.withSearchPanel = this.withSearchPanel && this.multi_record &&
                               params.withSearchPanel && !searchPanelDisabled;

        // the boolean parameter 'isEmbedded' determines if the view should be
        // considered as a subview. For now this is only used by the graph
        // controller that appends a 'Group By' button beside the 'Measures'
        // button when the graph view is embedded.
        var isEmbedded = params.isEmbedded || false;

        this.rendererParams = {
            arch: this.arch,
            isEmbedded: isEmbedded,
            noContentHelp: params.noContentHelp,
        };

        this.controllerParams = {
            actionViews: params.actionViews,
            activeActions: {
                edit: this.arch.attrs.edit ? !!JSON.parse(this.arch.attrs.edit) : true,
                create: this.arch.attrs.create ? !!JSON.parse(this.arch.attrs.create) : true,
                delete: this.arch.attrs.delete ? !!JSON.parse(this.arch.attrs.delete) : true,
                duplicate: this.arch.attrs.duplicate ? !!JSON.parse(this.arch.attrs.duplicate) : true,
            },
            bannerRoute: this.arch.attrs.banner_route,
            controllerID: params.controllerID,
            displayName: params.displayName,
            isEmbedded: isEmbedded,
            modelName: params.modelName,
            viewType: this.viewType,
            withControlPanel: this.withControlPanel,
            withSearchPanel: this.withSearchPanel,
        };

        var controllerState = params.controllerState || {};
        var currentId = controllerState.currentId || params.currentId;
        this.loadParams = {
            context: params.context,
            count: params.count || ((this.controllerParams.ids !== undefined) &&
                   this.controllerParams.ids.length) || 0,
            domain: params.domain,
            modelName: params.modelName,
            res_id: currentId,
            res_ids: controllerState.resIds || params.ids || (currentId ? [currentId] : undefined),
        };
        var defaultOrder = this.arch.attrs.default_order;
        if (defaultOrder) {
            this.loadParams.orderedBy = _.map(defaultOrder.split(','), function (order) {
                order = order.trim().split(' ');
                return {name: order[0], asc: order[1] !== 'desc'};
            });
        }
        if (params.searchQuery) {
            this._updateMVCParams(params.searchQuery);
        }

        if (this.withControlPanel) {
            this.controlPanelModelConfig = {
                env: Component.env,
                actionId: action.id,
                actionContext: Object.assign({}, this.loadParams.context || {}),
                actionDomain: this.loadParams.domain || [],
                modelName: params.modelName,
                // control initialization
                activateDefaultFavorite: params.activateDefaultFavorite,
                dynamicFilters: params.dynamicFilters,
                viewInfo: params.controlPanelFieldsView,
                withSearchBar: params.withSearchBar,
                // used to avoid timeRanges in query
                searchMenuTypes: params.searchMenuTypes,
                // avoid work to initialize
                importedState: controllerState.cpState,
            };

            const controlPanelModel = new ControlPanelModel(this.controlPanelModelConfig);

            const controlPanelProps = {
                action,
                breadcrumbs: params.breadcrumbs,
                controlPanelModel,
                fields: this.fields,
                searchMenuTypes: params.searchMenuTypes,
                view: this.fieldsView,
                views: action.views && action.views.filter(v => v.multiRecord === this.multi_record),
                withBreadcrumbs: params.withBreadcrumbs,
                withSearchBar: params.withSearchBar,
            };
            this.controllerParams.controlPanelModel = controlPanelModel;
            this.controllerParams.controlPanelProps = controlPanelProps;
        }

        if (this.withSearchPanel) {
            this.searchPanelParams = {
                arch: (params.controlPanelFieldsView || {}).arch,
                defaultNoFilter: params.searchPanelDefaultNoFilter,
                fields: this.fields,
                model: this.loadParams.modelName,
                state: controllerState.spState,
            };
        }
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    getController: async function (parent) {
        const _super = this._super.bind(this);
        if (this.withControlPanel) {
            await this.controllerParams.controlPanelModel.isReady;
            const query = this.controllerParams.controlPanelModel.getQuery();
            this._updateMVCParams(query);
        }
        let searchPanel = false;
        if (this.withSearchPanel) {
            const spProto = this.config.SearchPanel.prototype;
            const { arch, fields } = this.searchPanelParams;
            const searchPanelParams = spProto.computeSearchPanelParams(arch, fields, this.viewType);
            if (searchPanelParams.sections) {
                this.searchPanelParams.sections = searchPanelParams.sections;
                this.rendererParams.withSearchPanel = true;
                searchPanel = await this._createSearchPanel(parent, searchPanelParams);
            }
        }
        // get the parent of the model if it already exists, as _super will
        // set the new controller as parent, which we don't want
        const modelParent = this.model && this.model.getParent();
        const controller = await _super(...arguments);
        if (searchPanel) {
            searchPanel.setParent(controller);
        }
        if (modelParent) {
            // if we already add a model, restore its parent
            this.model.setParent(modelParent);
        }
        return controller;
    },
    /**
     * Ensures that only one instance of AbstractModel is created
     *
     * @override
     */
    getModel: function () {
        if (!this.model) {
            this.model = this._super.apply(this, arguments);
        }
        return this.model;
    },
    /**
     * This is useful to customize the actual class to use before calling
     * createView.
     *
     * @param {Controller} Controller
     */
    setController: function (Controller) {
        this.Controller = Controller;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Widget} parent
     * @returns {Promise<SearchPanel>} resolved when the searchPanel is ready
     */
    _createSearchPanel: async function (parent, params) {
        var defaultValues = {};
        Object.keys(this.loadParams.context).forEach((key) => {
            let match = /^searchpanel_default_(.*)$/.exec(key);
            if (match) {
                defaultValues[match[1]] = this.loadParams.context[key];
            }
        });
        var controlPanelDomain = this.loadParams.domain;
        const viewDomain = await this._getViewDomain(parent);
        var spParams = _.extend({}, this.searchPanelParams, {
            defaultValues: defaultValues,
            searchDomain: controlPanelDomain,
            viewDomain,
            classes: params.classes || [],
        });
        var searchPanel = new this.config.SearchPanel(parent, spParams);
        this.controllerParams.searchPanel = searchPanel;
        this.controllerParams.controlPanelDomain = controlPanelDomain;
        await searchPanel.appendTo(document.createDocumentFragment());

        var searchPanelDomain = searchPanel.getDomain();
        this.loadParams.domain = controlPanelDomain.concat(searchPanelDomain);
        return searchPanel;
    },
    /**
     * @private
     * @param {Object} [action]
     * @param {Object} [action.context || {}]
     * @param {boolean} [action.context.no_breadcrumbs=false]
     * @param {integer} [action.context.active_id]
     * @param {integer[]} [action.context.active_ids]
     * @param {Object} [action.controlPanelFieldsView]
     * @param {string} [action.display_name]
     * @param {Array[]} [action.domain=[]]
     * @param {string} [action.help]
     * @param {integer} [action.id]
     * @param {integer} [action.limit]
     * @param {string} [action.name]
     * @param {string} [action.res_model]
     * @param {string} [action.target]
     * @returns {Object}
     */
    _extractParamsFromAction: function (action) {
        action = action || {};
        var context = action.context || {};
        var inline = action.target === 'inline';
        return {
            actionId: action.id || false,
            actionViews: action.views || [],
            activateDefaultFavorite: !context.active_id && !context.active_ids,
            context: action.context || {},
            controlPanelFieldsView: action.controlPanelFieldsView,
            currentId: action.res_id ? action.res_id : undefined,  // load returns 0
            displayName: action.display_name || action.name,
            domain: action.domain || [],
            limit: action.limit,
            modelName: action.res_model,
            noContentHelp: action.help,
            searchMenuTypes: inline ? [] : this.searchMenuTypes,
            withBreadcrumbs: 'no_breadcrumbs' in context ? !context.no_breadcrumbs : true,
            withControlPanel: this.withControlPanel,
            withSearchBar: inline ? false : this.withSearchBar,
            withSearchPanel: this.withSearchPanel,
        };
    },
    /**
     * Get the domain defined by the view. It is meant to be overridden. The parent
     * is provided in case some subcomponents need to be retrieved.
     *
     * @private
     * @param {Object} parent
     * @returns {Promise<Array[]>}
     */
    _getViewDomain: async function (parent) {
        return [];
    },
    /**
     * Processes a fieldsView. In particular, parses its arch.
     *
     * @private
     * @param {Object} fieldsView
     * @param {string} fieldsView.arch
     * @returns {Object} the processed fieldsView
     */
    _processFieldsView: function (fieldsView) {
        var fv = _.extend({}, fieldsView);
        fv.arch = viewUtils.parseArch(fv.arch);
        fv.viewFields = _.defaults({}, fv.viewFields, fv.fields);
        return fv;
    },
    /**
     * Hook to update the renderer, controller and load params with the result
     * of a search (i.e. a context, a domain and a groupBy).
     *
     * @private
     * @param {Object} searchQuery
     * @param {Object} searchQuery.context
     * @param {Object} [searchQuery.timeRanges]
     * @param {Array[]} searchQuery.domain
     * @param {string[]} searchQuery.groupBy
     */
    _updateMVCParams: function (searchQuery) {
        this.loadParams = _.extend(this.loadParams, {
            context: searchQuery.context,
            domain: searchQuery.domain,
            groupedBy: searchQuery.groupBy,
        });
        this.loadParams.orderedBy = Array.isArray(searchQuery.orderedBy) && searchQuery.orderedBy.length ?
                                        searchQuery.orderedBy :
                                        this.loadParams.orderedBy;
        if (searchQuery.timeRanges) {
            this.loadParams.timeRanges = searchQuery.timeRanges;
            this.rendererParams.timeRanges = searchQuery.timeRanges;
        }
    },
});

return AbstractView;

});
