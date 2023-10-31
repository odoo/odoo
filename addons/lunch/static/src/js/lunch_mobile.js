odoo.define('lunch.LunchMobile', function (require) {
"use strict";

var config = require('web.config');
var LunchWidget = require('lunch.LunchWidget');
var LunchKanbanController = require('lunch.LunchKanbanController');
var LunchListController = require('lunch.LunchListController');

if (!config.device.isMobile) {
    return;
}

LunchWidget.include({
    template: "LunchWidgetMobile",

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

var mobileFunctions = {
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
    _renderLunchWidget: function () {
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
};

LunchKanbanController.include(mobileFunctions);
LunchListController.include(mobileFunctions);

});
