odoo.define('awesome_map.MapView', function (require) {
"use strict";

var MapController = require('awesome_map.MapController');
var MapModel = require('awesome_map.MapModel');
var MapRenderer = require('awesome_map.MapRenderer');
var AbstractView = require('web.AbstractView');
var core = require('web.core');
var viewRegistry = require('web.view_registry');

var _lt = core._lt;

var MapView = AbstractView.extend({
    display_name: _lt('Map'),
    icon: 'fa-globe',
    cssLibs: ['/awesome_map/static/lib/leaflet/leaflet.css'],
    jsLibs: ['/awesome_map/static/lib/leaflet/leaflet.js'],
    config: {
        Model: MapModel,
        Controller: MapController,
        Renderer: MapRenderer,
    },
    /**
     * @override
     */
    init: function (viewInfo) {
        this._super.apply(this, arguments);
        this.loadParams.latitudeField = viewInfo.arch.attrs.latitude;
        this.loadParams.longitudeField = viewInfo.arch.attrs.longitude;
    },
});

viewRegistry.add('map', MapView);

});