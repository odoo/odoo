odoo.define('web.mvc', function (require) {
"use strict";

/**
 * This file contains a 'formalization' of a MVC pattern, applied to Odoo
 * idioms.
 *
 * For a simple widget/component, this is definitely overkill.  However, when
 * working on complex systems, such as Odoo views (or the control panel, or some
 * client actions), it is useful to clearly separate the code in concerns.
 *
 * We define here 4 classes: Factory, Model, Renderer, Controller.  Note that
 * for various historical reasons, we use the term Renderer instead of View. The
 * main issue is that the term 'View' is used way too much in Odoo land, and
 * adding it would increase the confusion.
 *
 * In short, here are the responsabilities of the four classes:
 * - Model: this is where the main state of the system lives.  This is the part
 *     that will talk to the server, process the results and is the owner of the
 *     state
 * - Renderer: this is the UI code: it should only be concerned with the look
 *     and feel of the system: rendering, binding handlers, ...
 * - Controller: coordinates the model with the renderer and the parents widgets.
 *     This is more a 'plumbing' widget.
 * - Factory: setting up the MRC components is a complex task, because each of
 *     them needs the proper arguments/options, it needs to be extensible, they
 *     needs to be created in the proper order, ...  The job of the factory is
 *     to process all the various arguments, and make sure each component is as
 *     simple as possible.
 */

var Class = require('web.Class');
var mixins = require('web.mixins');
var ServicesMixin = require('web.ServicesMixin');
var Widget = require('web.Widget');
const { loadBundle } = require('@web/core/assets');


/**
 * Owner of the state, this component is tasked with fetching data, processing
 * it, updating it, ...
 *
 * Note that this is not a widget: it is a class which has not UI representation.
 *
 * @class Model
 */
var Model = Class.extend(mixins.EventDispatcherMixin, ServicesMixin, {
    /**
     * @param {Widget} parent
     * @param {Object} params
     */
    init: function (parent, params) {
        mixins.EventDispatcherMixin.init.call(this);
        this.setParent(parent);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * This method should return the complete state necessary for the renderer
     * to display the current data.
     *
     * @returns {*}
     */
    get: function () {
    },
    /**
     * The load method is called once in a model, when we load the data for the
     * first time.  The method returns (a promise that resolves to) some kind
     * of token/handle.  The handle can then be used with the get method to
     * access a representation of the data.
     *
     * @param {Object} params
     * @returns {Promise} The promise resolves to some kind of handle
     */
    load: function () {
        return Promise.resolve();
    },
});

/**
 * Only responsibility of this component is to display the user interface, and
 * react to user changes.
 *
 * @class Renderer
 */
var Renderer = Widget.extend({
    /**
     * @override
     * @param {any} state
     * @param {Object} params
     */
    init: function (parent, state, params) {
        this._super(parent);
        this.state = state;
    },
});

/**
 * The controller has to coordinate between parent, renderer and model.
 *
 * @class Controller
 */
var Controller = Widget.extend({
    /**
     * @override
     * @param {Model} model
     * @param {Renderer} renderer
     * @param {Object} params
     * @param {any} [params.handle=null]
     */
    init: function (parent, model, renderer, params) {
        this._super.apply(this, arguments);
        this.handle = params.handle || null;
        this.model = model;
        this.renderer = renderer;
    },
    /**
     * @returns {Promise}
     */
    start: function () {
        return Promise.all(
            [this._super.apply(this, arguments),
            this._startRenderer()]
        );
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Appends the renderer in the $el. To override to insert it elsewhere.
     *
     * @private
     */
    _startRenderer: function () {
        return this.renderer.appendTo(this.$el);
    },
});

var Factory = Class.extend({
    config: {
        Model: Model,
        Renderer: Renderer,
        Controller: Controller,
    },
    /**
     * @override
     */
    init: function () {
        this.rendererParams = {};
        this.controllerParams = {};
        this.modelParams = {};
        this.loadParams = {};
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Main method of the Factory class. Create a controller, and make sure that
     * data and libraries are loaded.
     *
     * There is a unusual thing going in this method with parents: we create
     * renderer/model with parent as parent, then we have to reassign them at
     * the end to make sure that we have the proper relationships.  This is
     * necessary to solve the problem that the controller needs the model and
     * the renderer to be instantiated, but the model need a parent to be able
     * to load itself, and the renderer needs the data in its constructor.
     *
     * @param {Widget} parent the parent of the resulting Controller (most
     *      likely an action manager)
     * @returns {Promise<Controller>}
     */
    getController: function (parent) {
        var self = this;
        var model = this.getModel(parent);
        return Promise.all([this._loadData(model), loadBundle(this)]).then(function (result) {
            const { state, handle } = result[0];
            var renderer = self.getRenderer(parent, state);
            var Controller = self.Controller || self.config.Controller;
            const initialState = model.get(handle);
            var controllerParams = _.extend({
                initialState,
                handle,
            }, self.controllerParams);
            var controller = new Controller(parent, model, renderer, controllerParams);
            model.setParent(controller);
            renderer.setParent(controller);
            return controller;
        });
    },
    /**
     * Returns a new model instance
     *
     * @param {Widget} parent the parent of the model
     * @returns {Model} instance of the model
     */
    getModel: function (parent) {
        var Model = this.config.Model;
        return new Model(parent, this.modelParams);
    },
    /**
     * Returns a new renderer instance
     *
     * @param {Widget} parent the parent of the renderer
     * @param {Object} state the information related to the rendered data
     * @returns {Renderer} instance of the renderer
     */
    getRenderer: function (parent, state) {
        var Renderer = this.config.Renderer;
        return new Renderer(parent, state, this.rendererParams);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Loads initial data from the model
     *
     * @private
     * @param {Model} model a Model instance
     * @param {Object} [options={}]
     * @param {boolean} [options.withSampleData=true]
     * @returns {Promise<*>} a promise that resolves to the value returned by
     *   the get method from the model
     * @todo: get rid of loadParams (use modelParams instead)
     */
    _loadData: function (model, options = {}) {
        options.withSampleData = 'withSampleData' in options ? options.withSampleData : true;
        return model.load(this.loadParams).then(function (handle) {
            return { state: model.get(handle, options), handle };
        });
    },
});


return {
    Factory: Factory,
    Model: Model,
    Renderer: Renderer,
    Controller: Controller,
};

});
