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

var ajax = require('web.ajax');
var Class = require('web.Class');
var AbstractModel = require('web.AbstractModel');
var AbstractRenderer = require('web.AbstractRenderer');
var AbstractController = require('web.AbstractController');
var utils = require('web.utils');

var AbstractView = Class.extend({
    // name displayed in view switchers
    display_name: '',
    // indicates whether or not the view is mobile-friendly
    mobile_friendly: false,
    // icon is the font-awesome icon to display in the view switcher
    icon: 'fa-question',
    // multi_record is used to distinguish views displaying a single record
    // (e.g. FormView) from those that display several records (e.g. ListView)
    multi_record: true,
    // determine if a search view should be displayed in the control panel and
    // allowed to interact with the view.  Currently, the only not searchable
    // views are the form view and the diagram view.
    searchable: true,
    // viewType is the type of the view, like 'form', 'kanban', 'list'...
    viewType: undefined,
    // if searchable, this flag determines if the search view will display a
    // groupby menu or not.  This is useful for the views which do not support
    // grouping data.
    groupable: true,
    enableTimeRangeMenu: false,
    config: {
        Model: AbstractModel,
        Renderer: AbstractRenderer,
        Controller: AbstractController,
    },

    /**
     * The constructor function is supposed to set 3 variables: rendererParams,
     * controllerParams and loadParams.  These values will be used to initialize
     * the model, renderer and controllers.
     *
     * @constructs AbstractView
     *
     * @param {Object} viewInfo
     * @param {Object} viewInfo.arch
     * @param {Object} viewInfo.fields
     * @param {Object} viewInfo.fieldsInfo
     * @param {Object} params
     * @param {string} params.modelName The actual model name
     * @param {Object} params.context
     * @param {number} [params.count]
     * @param {string} [params.controllerID]
     * @param {string[]} params.domain
     * @param {string[][]} params.timeRange
     * @param {string[][]} params.comparisonTimeRange
     * @param {string} params.timeRangeDescription
     * @param {string} params.comparisonTimeRangeDescription
     * @param {boolean} params.compare
     * @param {string[]} params.groupBy
     * @param {number} [params.currentId]
     * @param {boolean} params.isEmbedded
     * @param {number[]} [params.ids]
     * @param {boolean} [params.withControlPanel]
     * @param {boolean} [params.action.flags.headless]
     * @param {string} [params.action.display_name]
     * @param {string} [params.action.name]
     * @param {string} [params.action.help]
     * @param {string} [params.action.jsID]
     * @param {boolean} [params.action.views]
     */
    init: function (viewInfo, params) {
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
        this.fields = this.fieldsView.viewFields;
        this.arch = this.fieldsView.arch;
        // the boolean parameter 'isEmbedded' determines if the view should be considered
        // as a subview. For now this is only used by the graph controller that appends a
        // 'Group By' button beside the 'Measures' button when the graph view is embedded.
        var isEmbedded = params.isEmbedded || false;

        // The noContentHelper's message can be empty, i.e. either a real empty string
        // or an empty html tag. In both cases, we consider the helper empty.
        var help = params.action && params.action.help || "";
        var htmlHelp = document.createElement("div");
        htmlHelp.innerHTML = help;
        this.rendererParams = {
            arch: this.arch,
            isEmbedded: isEmbedded,
            noContentHelp: htmlHelp.innerText.trim() ? help : "",
        };

        var timeRangeMenuData = params.context.timeRangeMenuData;
        var timeRange = [];
        var comparisonTimeRange = [];
        var compare = false;
        var timeRangeDescription = "";
        var comparisonTimeRangeDescription = "";
        if (this.enableTimeRangeMenu && timeRangeMenuData) {
            timeRange = timeRangeMenuData.timeRange;
            comparisonTimeRange = timeRangeMenuData.comparisonTimeRange;
            compare = comparisonTimeRange.length > 0;
            timeRangeDescription = timeRangeMenuData.timeRangeDescription;
            comparisonTimeRangeDescription = timeRangeMenuData.comparisonTimeRangeDescription;
            this.rendererParams.timeRangeDescription = timeRangeDescription;
            this.rendererParams.comparisonTimeRangeDescription = comparisonTimeRangeDescription;
        }

        this.controllerParams = {
            modelName: params.modelName,
            activeActions: {
                edit: this.arch.attrs.edit ? JSON.parse(this.arch.attrs.edit) : true,
                create: this.arch.attrs.create ? JSON.parse(this.arch.attrs.create) : true,
                delete: this.arch.attrs.delete ? JSON.parse(this.arch.attrs.delete) : true,
                duplicate: this.arch.attrs.duplicate ? JSON.parse(this.arch.attrs.duplicate) : true,
            },
            groupable: this.groupable,
            enableTimeRangeMenu: this.enableTimeRangeMenu,
            isEmbedded: isEmbedded,
            controllerID: params.controllerID,
            bannerRoute: this.arch.attrs.banner_route,
        };
        // AAB: these params won't be necessary as soon as the ControlPanel will
        // be instantiated by the View
        this.controllerParams.displayName = params.action && (params.action.display_name || params.action.name);
        this.controllerParams.isMultiRecord = this.multi_record;
        this.controllerParams.searchable = this.searchable;
        this.controllerParams.searchView = params.action && params.action.searchView;
        this.controllerParams.searchViewHidden = this.searchview_hidden; // AAB: use searchable instead where it is used?
        this.controllerParams.actionViews = params.action ? params.action.views : [];
        this.controllerParams.viewType = this.viewType;
        this.controllerParams.withControlPanel = true;
        if (params.action && params.action.flags) {
            this.controllerParams.withControlPanel = !params.action.flags.headless;
        } else if ('withControlPanel' in params) {
            this.controllerParams.withControlPanel = params.withControlPanel;
        }

        // set groupBy only if view is groupable
        var groupBy = [];
        if (this.groupable) {
            groupBy = params.groupBy;
            if (typeof groupBy === 'string') {
                groupBy = [groupBy];
            }
        }

        this.loadParams = {
            context: params.context,
            count: params.count || ((this.controllerParams.ids !== undefined) &&
                   this.controllerParams.ids.length) || 0,
            domain: params.domain,
            timeRange: timeRange,
            timeRangeDescription: timeRangeDescription,
            comparisonTimeRange: comparisonTimeRange,
            comparisonTimeRangeDescription: comparisonTimeRangeDescription,
            compare: compare,
            groupedBy: groupBy,
            modelName: params.modelName,
            res_id: params.currentId,
            res_ids: params.ids,
            orderedBy: params.context ? params.context.orderedBy : [],
        };
        if (params.modelName) {
            this.loadParams.modelName = params.modelName;
        }
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

        this.userContext = params.userContext;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Main method of the view class. Create a controller, and make sure that
     * data and libraries are loaded.
     *
     * There is a unusual thing going in this method with parents: we create
     * renderer/model with parent as parent, then we have to reassign them at
     * the end to make sure that we have the proper relationships.  This is
     * necessary to solve the problem that the controller need the model and the
     * renderer to be instantiated, but the model need a parent to be able to
     * load itself, and the renderer needs the data in its constructor.
     *
     * @param {Widget} parent The parent of the resulting Controller (most
     *      likely an action manager)
     * @returns {Deferred} The deferred resolves to a controller
     */
    getController: function (parent) {
        var self = this;
        // check if a model already exists, as if not, one will be created and
        // we'll have to set the controller as its parent
        var alreadyHasModel = !!this.model;
        return $.when(this._loadData(parent), ajax.loadLibs(this)).then(function () {
            var state = self.model.get(arguments[0]);
            var renderer = self.getRenderer(parent, state);
            var Controller = self.Controller || self.config.Controller;
            var controllerParams = _.extend({
                initialState: state,
            }, self.controllerParams);
            var controller = new Controller(parent, self.model, renderer, controllerParams);
            renderer.setParent(controller);

            if (!alreadyHasModel) {
                // if we have a model, it already has a parent. Otherwise, we
                // set the controller, so the rpcs from the model actually work
                self.model.setParent(controller);
            }
            return controller;
        });
    },
    /**
     * Returns the view model or create an instance of it if none
     *
     * @param {Widget} parent the parent of the model, if it has to be created
     * @return {Object} instance of the view model
     */
    getModel: function (parent) {
        if (!this.model) {
            var Model = this.config.Model;
            this.model = new Model(parent);
        }
        return this.model;
    },
    /**
     * Returns the a new view renderer instance
     *
     * @param {Widget} parent the parent of the model, if it has to be created
     * @param {Object} state the information related to the rendered view
     * @return {Object} instance of the view renderer
     */
    getRenderer: function (parent, state) {
        var Renderer = this.config.Renderer;
        return new Renderer(parent, state, this.rendererParams);
    },
    /**
     * this is useful to customize the actual class to use before calling
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
     * Load initial data from the model
     *
     * @private
     * @param {Widget} parent the parent of the model
     * @returns {Deferred<*>} a deferred that resolves to whatever the model
     *   decide to return
     */
    _loadData: function (parent) {
        var model = this.getModel(parent);
        return model.load(this.loadParams);
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
        var doc = $.parseXML(fv.arch).documentElement;
        var stripWhitespaces = doc.nodeName.toLowerCase() !== 'kanban';
        fv.arch = utils.xml_to_json(doc, stripWhitespaces);
        fv.viewFields = _.defaults({}, fv.viewFields, fv.fields);
        return fv;
    },
});

return AbstractView;

});

odoo.define('web.viewUtils', function () {
"use strict";

/**
 * FIXME: move this module to its own file in master
 */

var utils = {
    /**
     * Returns the value of a group dataPoint, i.e. the value of the groupBy
     * field for the records in that group.
     *
     * @param {Object} group dataPoint of type list, corresponding to a group
     * @param {string} groupByField the name of the groupBy field
     * @returns {string | integer | false}
     */
    getGroupValue: function (group, groupByField) {
        var groupedByField = group.fields[groupByField];
        switch (groupedByField.type) {
            case 'many2one':
                return group.res_id || false;
            case 'selection':
                var descriptor = _.findWhere(groupedByField.selection, group.value);
                return descriptor && descriptor[0];
            default:
                return group.value;
        }
    },
    /**
     * States whether or not the quick create feature is available for the given
     * datapoint, depending on its groupBy field.
     *
     * @param {Object} list dataPoint of type list
     * @returns {Boolean} true iff the kanban quick create feature is available
     */
    isQuickCreateEnabled: function (list) {
        var groupByField = list.groupedBy[0] && list.groupedBy[0].split(':')[0];
        if (!groupByField) {
            return false;
        }
        var availableTypes = ['char', 'boolean', 'many2one', 'selection'];
        if (!_.contains(availableTypes, list.fields[groupByField].type)) {
            return false;
        }
        return true;
    },
};

return utils;

});
