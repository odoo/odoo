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
 * 2. call the createController method on the view instance. This returns a
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
     * @param {any} arch
     * @param {any} fields
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
    init: function (arch, fields, params) {
        this.rendererParams = {
            arch: arch
        };

        this.controllerParams = {
            modelName: params.modelName,
            activeActions: {
                edit: arch.attrs.edit ? JSON.parse(arch.attrs.edit) : true,
                create: arch.attrs.create ? JSON.parse(arch.attrs.create) : true,
                delete: arch.attrs.delete ? JSON.parse(arch.attrs.delete) : true,
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
    createController: function (parent) {
        var self = this;
        var model = this.model || this.createModel(parent);
        return $.when(model.load(this.loadParams), this._loadLibs()).then(function () {
            var state = model.get(arguments[0]);
            var renderer = self.createRenderer(parent, state);
            var Controller = self.config.Controller;
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
    createModel: function (parent) {
        var Model = this.config.Model;
        return new Model(parent);
    },
    createRenderer: function (parent, state) {
        var Renderer = this.config.Renderer;
        return new Renderer(parent, state, this.rendererParams);
    },
    /**
     * this is usedful to customize the actual class to use before calling
     * createView.
     *
     * @param {Controller} Controller
     */
    setController: function (Controller) {
        this.config.Controller = Controller;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

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
        _.each(this.config.js_libs, function (url) {
            defs.push(ajax.loadJS(url));
        });
        _.each(this.config.css_libs, function (url) {
            defs.push(ajax.loadCSS(url));
        });
        return $.when.apply($, defs);
    },
});

return AbstractView;

});
