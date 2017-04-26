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

var Class = require('web.Class');
var ajax = require('web.ajax');
var AbstractModel = require('web.AbstractModel');
var AbstractRenderer = require('web.AbstractRenderer');
var AbstractController = require('web.AbstractController');

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

    config: {
        Model: AbstractModel,
        Renderer: AbstractRenderer,
        Controller: AbstractController,
        js_libs: [],
        css_libs: [],
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
     * @param {string[]} params.domain
     * @param {string[]} params.groupBy
     * @param {number} [params.currentId]
     * @param {number[]} [params.ids]
     * @param {string} [params.action.help]
     */
    init: function (viewInfo, params) {
        this.rendererParams = {
            arch: viewInfo.arch,
        };

        this.controllerParams = {
            modelName: params.modelName,
            activeActions: {
                edit: viewInfo.arch.attrs.edit ? JSON.parse(viewInfo.arch.attrs.edit) : true,
                create: viewInfo.arch.attrs.create ? JSON.parse(viewInfo.arch.attrs.create) : true,
                delete: viewInfo.arch.attrs.delete ? JSON.parse(viewInfo.arch.attrs.delete) : true,
            },
            noContentHelp: params.action && params.action.help,
        };

        this.loadParams = {
            context: params.context,
            count: params.count || ((this.controllerParams.ids !== undefined) &&
                   this.controllerParams.ids.length) || 0,
            domain: params.domain,
            groupedBy: params.groupBy,
            modelName: params.modelName,
            res_id: params.currentId,
            res_ids: params.ids,
        };
        if (params.modelName) {
            this.loadParams.modelName = params.modelName;
        }

        this.userContext = params.userContext;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Main method of the view class.
     *
     * @param {Widget} parent The parent of the resulting Controller (most
     *      likely a view manager)
     * @returns {Deferred} The deferred resolves to a controller
     */
    getController: function (parent) {
        var self = this;
        return $.when(this._loadData(parent), this._loadLibs()).then(function () {
            var model = self.getModel();
            var state = model.get(arguments[0]);
            var renderer = self.getRenderer(parent, state);
            var Controller = self.Controller || self.config.Controller;
            var controllerParams = _.extend({
                initialState: state,
            }, self.controllerParams);
            var controller = new Controller(parent, model, renderer, controllerParams);
            renderer.setParent(controller);

            if (!self.model) {
                // if we have a model, it already has a parent. Otherwise, we
                // set the controller, so the rpcs from the model actually work
                model.setParent(controller);
            }
            return controller;
        });
    },
    getModel: function (parent) {
        if (!this.model) {
            var Model = this.config.Model;
            this.model = new Model(parent);
        }
        return this.model;
    },
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
     * @param {Widget} parent the parent of the model, if it has to be created
     * @returns {Deferred<*>} a deferred that resolves to whatever the model
     *   decide to return
     */
    _loadData: function (parent) {
        var model = this.getModel(parent);
        return model.load(this.loadParams);
    },
    /**
     * Makes sure that the js_libs and css_libs are properly loaded. Note that
     * the ajax loadJS and loadCSS methods don't do anything if the given file
     * is already loaded.
     *
     * @private
     * @returns {Deferred}
     */
    _loadLibs: function () {
        var defs = [];
        var jsDefs;
        _.each(this.config.js_libs, function (urls) {
            if (typeof(urls) === 'string') {
                // js_libs is an array of urls: those urls can be loaded in
                // parallel
                defs.push(ajax.loadJS(urls));
            } else {
                // js_libs is an array of arrays of urls: those arrays of urls
                // must be loaded sequentially, but the urls inside each
                // sub-array can be loaded in parallel
                defs.push($.when.apply($, jsDefs).then(function () {
                    jsDefs = [];
                    _.each(urls, function (url) {
                        jsDefs.push(ajax.loadJS(url));
                    });
                    return $.when.apply($, jsDefs);
                }));
            }
        });
        _.each(this.config.css_libs, function (url) {
            defs.push(ajax.loadCSS(url));
        });
        return $.when.apply($, defs);
    },
});

return AbstractView;

});
