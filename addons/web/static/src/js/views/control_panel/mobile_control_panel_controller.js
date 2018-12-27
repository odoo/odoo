 odoo.define('web.MobileControlPanelController', function (require) {
"use strict";

var config = require('web.config');
var ControlPanelController = require('web.ControlPanelController');

if (!config.device.isMobile) {
    return;
}

ControlPanelController.include({
    custom_events:_.extend({}, ControlPanelController.prototype.custom_events, {
        'search_bar_cleared': '_onSearchBarCleared',
    }),

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * There is a 'Clear' button in the mobile control panel view.
     *
     * @private
     */
    _onSearchBarCleared: function () {
        var self = this;
        this.model.get().query.forEach(function (groupId) {
            self.model.deactivateGroup(groupId);
        });
        this._reportNewQueryAndRender();
    },
});

});
