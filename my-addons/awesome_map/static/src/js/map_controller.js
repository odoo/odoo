odoo.define('awesome_map.MapController', function (require) {
"use strict";

var AbstractController = require('web.AbstractController');
var core = require('web.core');

var qweb = core.qweb;

var MapController = AbstractController.extend({
    custom_events: {
        'record_clicked': '_onRecordClicked',
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    renderButtons: function ($node) {
        var self = this;
        this.$buttons = $(qweb.render("MapView.buttons", {widget: this}));
        this.$buttons.on('click', 'button.o_map_zoom_in', function () {
            self.renderer.zoomIn();
        });
        this.$buttons.on('click', 'button.o_map_zoom_out', function () {
            self.renderer.zoomOut();
        });
        this.$buttons.appendTo($node);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------
    /**
     * @param {OdooEvent} event
     */
    _onRecordClicked: function (event) {
        this.trigger_up('switch_view', {
            view_type: 'form',
            res_id: event.data.id,
            mode: 'readonly',
            model: this.modelName,
        });
    },
});

return MapController;

});