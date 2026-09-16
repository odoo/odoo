odoo.define('mapsly_frame_view.MapslyFrameView', function (require) {
"use strict";


var AbstractController = require('web.AbstractController');
var AbstractModel = require('web.AbstractModel');
var AbstractRenderer = require('web.AbstractRenderer');
var AbstractView = require('web.AbstractView');
var viewRegistry = require('web.view_registry');
var rpc = require('web.rpc');

var MapslyFrameController = AbstractController.extend({});
var MapslyFrameRenderer = AbstractRenderer.extend({
    className: "o_mapsly_frame_view",
	_render: function () {
	    const el = this.$el;
        rpc.query({
            model: 'ir.config_parameter',
            method: 'get_param',
            args: ['mapsly.mapsly_adapter_server']
        }).then(function (subdomain) {
            if (!subdomain) {
                subdomain = 'app';
            }
            const url = 'https://' + subdomain + '.mapsly.com';
            el.append(
                $('<iframe src="' + url + '" width="100%" height="100%" marginwidth="0" marginheight="0" frameborder="no" scrolling="no" style="border-width:0px; width:100%; height:100%;"></iframe>')
            );
            return $.when();
        });
	},
});
var MapslyFrameModel = AbstractModel.extend({

});

var MapslyFrameView = AbstractView.extend({
    config: {
        Model: MapslyFrameModel,
        Controller: MapslyFrameController,
        Renderer: MapslyFrameRenderer,
    },
    viewType: 'mapsly_frame',
    groupable: false,
    searchable: false,
    withSearchBar: false,
    withControlPanel: false,
    withSearchPanel: false,

    init: function () {
        this._super.apply(this, arguments);
    },
});

viewRegistry.add('mapsly_frame', MapslyFrameView);

return MapslyFrameView;

});