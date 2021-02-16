odoo.define('formio.BuilderController', function (require) {
"use strict";

var BasicController = require('web.BasicController');
var core = require('web.core');

var BuilderController = BasicController.extend({
    /**
     * @override
     *
     * @param {boolean} params.foo
     * @param {Object} params.bar
     */
    init: function (parent, model, renderer, params) {
        this._super.apply(this, arguments);
    },

    /**
     * Force mode back to readonly. Whenever we leave a form view, it is saved,
     * and should no longer be in edit mode.
     *
     * @override
     */
    willRestore: function () {
        this.mode = 'readonly';
    },

    /**
     * @override method from AbstractController
     * @returns {string}
     */
    getTitle: function () {
        return this.model.getName(this.handle);
    },

    /**
     * Updates the controller's title according to the new state
     *
     * @override
     * @private
     * @param {Object} state
     * @returns {Deferred}
     */
    _update: function () {
        var title = this.getTitle();
        this.set('title', title);
        return this._super.apply(this, arguments);
    },

    /**
     * We just add the current ID to the state pushed. This allows the web
     * client to add it in the url, for example.
     *
     * @override method from AbstractController
     * @private
     * @param {Object} [state]
     */
    _pushState: function (state) {
        var state = state || {};
        var env = this.model.get(this.handle, {env: true});
        state.id = env.currentId;
        this._super(state);
    },

});

return BuilderController;

});
