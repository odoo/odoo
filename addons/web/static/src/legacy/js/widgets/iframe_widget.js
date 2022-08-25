odoo.define('web.IFrameWidget', function (require) {
"use strict";

var Widget = require('web.Widget');

/**
 * Generic widget to create an iframe that listens for clicks
 *
 * It should be extended by overwriting the methods::
 *
 *      init: function(parent) {
 *          this._super(parent, <url_of_iframe>);
 *      },
 *      _onIFrameClicked: function(e){
 *          filter the clicks you want to use and apply
 *          an action on it
 *      }
 */
var IFrameWidget = Widget.extend({
    tagName: 'iframe',
    /**
     * @constructor
     * @param {Widget} parent
     * @param {string} url
     */
    init: function (parent, url) {
        this._super(parent);
        this.url = url;
    },
    /**
     * @override
     * @returns {Promise}
     */
    start: function () {
        this.$el.css({height: '100%', width: '100%', border: 0});
        this.$el.attr({src: this.url});
        this.$el.on("load", this._bindEvents.bind(this));
        return this._super();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Called when the iframe is ready
     */
    _bindEvents: function (){
        this.$el.contents().click(this._onIFrameClicked.bind(this));
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @param {MouseEvent} event
     */
    _onIFrameClicked: function (event){
    }
});

return IFrameWidget;

});
