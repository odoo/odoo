odoo.define('web.AbstractModel', function (require) {
"use strict";

/**
 * An AbstractModel is the M in MVC.  We tend to think of MVC more on the server
 * side, but we are talking here on the web client side.
 *
 * The duties of the Model are to fetch all relevant data, and to make them
 * available for the rest of the view.  Also, every modification to that data
 * should pass through the model.
 *
 * Note that the model is not a widget, it does not need to be rendered or
 * appended to the dom.  However, it inherits from the EventDispatcherMixin,
 * in order to be able to notify its parent by bubbling events up.
 */

var Class = require('web.Class');
var mixins = require('web.mixins');
var ServicesMixin = require('web.ServicesMixin');

var AbstractModel = Class.extend(mixins.EventDispatcherMixin, ServicesMixin, {
    /**
     * @param {Widget} parent
     */
    init: function (parent) {
        mixins.EventDispatcherMixin.init.call(this);
        this.setParent(parent);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * This method should return the complete state necessary for the renderer
     * to display the currently viewed data.
     *
     * @returns {*}
     */
    get: function () {
    },
    /**
     * The load method is called once in a model, when we load the data for the
     * first time.  The method returns (a deferred that resolves to) some kind
     * of token/handle.  The handle can then be used with the get method to
     * access a representation of the data.
     *
     * @param {Object} params
     * @param {string} params.modelName the name of the model
     * @returns {Deferred} The deferred resolves to some kind of handle
     */
    load: function (params) {
        return $.when();
    },
    /**
     * When something changes, the data may need to be refetched.  This is the
     * job for this method: reloading (only if necessary) all the data and
     * making sure that they are ready to be redisplayed.
     *
     * @param {Object} params
     * @returns {Deferred}
     */
    reload: function (params) {
        return $.when();
    },
});

return AbstractModel;

});
