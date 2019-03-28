odoo.define('lunch.LunchKanbanMobile', function (require) {
"use strict";

var config = require('web.config');
var LunchKanbanWidget = require('lunch.LunchKanbanWidget');
var LunchKanbanController = require('lunch.LunchKanbanController');

if (!config.device.isMobile) {
    return;
}

LunchKanbanWidget.include({
    template: "LunchKanbanWidgetMobile",

    /**
     * Override to set the toggle state allowing initially open it.
     *
     * @override
     */
    init: function (parent, params) {
        this._super.apply(this, arguments);
        this.keepOpen = params.keepOpen || undefined;
    },
});

LunchKanbanController.include({
    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        this.openWidget = false;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Override to add the widget's toggle state to its data.
     *
     * @override
     * @private
     */
    _renderLunchKanbanWidget: function () {
        this.widgetData.keepOpen = this.openWidget;
        this.openWidget = false;
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     */
    _onAddProduct: function () {
        this.openWidget = true;
        this._super.apply(this, arguments);
    },

    /**
     * @override
     * @private
     */
    _onRemoveProduct: function () {
        this.openWidget = true;
        this._super.apply(this, arguments);
    },
});

});
