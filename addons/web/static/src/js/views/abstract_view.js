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
var ControlPanelView = require('web.ControlPanelView');
var mvc = require('web.mvc');
var viewUtils = require('web.viewUtils');

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
    // determines the MVC components to use
    config: _.extend({}, Factory.prototype.config, {
        Model: AbstractModel,
        Renderer: AbstractRenderer,
        Controller: AbstractController,
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
     * @param {string} [params.controllerState]
     * @param {string} [params.displayName]
     * @param {Array[]} [params.domain=[]]
     * @param {Object[]} [params.dynamicFilters] transmitted to the
     *   ControlPanelView
     * @param {number[]} [params.ids]
     * @param {boolean} [params.isEmbedded=false]
     * @param {Object} [params.searchQuery={}]
     * @param {Object} [params.searchQuery.context={}]
     * @param {Array[]} [params.searchQuery.domain=[]]
     * @param {string[]} [params.searchQuery.groupBy=[]]
     * @param {Object} [params.userContext={}]
     * @param {boolean} [params.withControlPanel=true]
     */
    init: function (viewInfo, params) {
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
            isMultiRecord: this.multi_record,
            modelName: params.modelName,
            viewType: this.viewType,
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
        // default_order is like:
        //   'name,id desc'
        // but we need it like:
        //   [{name: 'id', asc: false}, {name: 'name', asc: true}]
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

        this.controlPanelParams = {
            action: action,
            activateDefaultFavorite: params.activateDefaultFavorite,
            dynamicFilters: params.dynamicFilters,
            breadcrumbs: params.breadcrumbs,
            context: this.loadParams.context,
            domain: this.loadParams.domain,
            modelName: params.modelName,
            searchMenuTypes: params.searchMenuTypes,
            state: controllerState.cpState,
            viewInfo: params.controlPanelFieldsView,
            withBreadcrumbs: params.withBreadcrumbs,
            withSearchBar: params.withSearchBar,
        };
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    getController: function (parent) {
        var self = this;
        var def;
        if (this.withControlPanel) {
            def = this._createControlPanel(parent);
        }
        var _super = this._super.bind(this);
        return Promise.resolve(def).then(function (controlPanel) {
            // get the parent of the model if it already exists, as _super will
            // set the new controller as parent, which we don't want
            var modelParent = self.model && self.model.getParent();
            var prom =  _super(parent);
            prom.then(function (controller) {
                if (controlPanel) {
                    controlPanel.setParent(controller);
                }
                if (modelParent) {
                    // if we already add a model, restore its parent
                    self.model.setParent(modelParent);
                }
            });
            return prom;
        });
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
     * Instantiates and starts a ControlPanelController.
     *
     * @private
     * @param {Widget} parent
     * @returns {ControlPanelController}
     */
    _createControlPanel: function (parent) {
        var self = this;
        var controlPanelView = new ControlPanelView(this.controlPanelParams);
        return controlPanelView.getController(parent).then(function (controlPanel) {
            self.controllerParams.controlPanel = controlPanel;
            return controlPanel.appendTo(document.createDocumentFragment()).then(function () {
                self._updateMVCParams(controlPanel.getSearchQuery());
                return controlPanel;
            });
        });
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
        };
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
     * @param {Object} [searchQuery.context.timeRangeMenuData={}]
     * @param {Array[]} [searchQuery.context.timeRangeMenuData.comparisonTimeRange=[]]
     * @param {string} [searchQuery.context.timeRangeMenuData.comparisonTimeRangeDescription='']
     * @param {string} [searchQuery.context.timeRangeMenuData.timeRangeDescription='']
     * @param {Array[]} [searchQuery.context.timeRangeMenuData.timeRange=[]]
     * @param {Array[]} searchQuery.domain
     * @param {string[]} searchQuery.groupBy
     */
    _updateMVCParams: function (searchQuery) {
        var timeRangeMenuData = searchQuery.context.timeRangeMenuData || {};
        var comparisonTimeRange = timeRangeMenuData.comparisonTimeRange || [];
        var comparisonTimeRangeDescription = timeRangeMenuData.comparisonTimeRangeDescription || '';
        var timeRangeDescription = timeRangeMenuData.timeRangeDescription || '';
        this.loadParams = _.extend(this.loadParams, {
            compare: comparisonTimeRange.length > 0,
            comparisonField: timeRangeMenuData.comparisonField,
            comparisonTimeRange: comparisonTimeRange,
            comparisonTimeRangeDescription: comparisonTimeRangeDescription,
            context: searchQuery.context,
            domain: searchQuery.domain,
            groupedBy: searchQuery.groupBy,
            timeRange: timeRangeMenuData.timeRange || [],
            timeRangeDescription: timeRangeMenuData.timeRangeDescription || '',
        });
        this.loadParams.orderedBy = searchQuery.orderedBy ? searchQuery.orderedBy : this.loadParams.orderedBy;
        this.rendererParams.timeRangeDescription = timeRangeDescription;
        this.rendererParams.comparisonTimeRangeDescription = comparisonTimeRangeDescription;
    },
});

return AbstractView;

});
