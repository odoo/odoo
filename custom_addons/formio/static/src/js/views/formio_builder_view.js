odoo.define('formio.BuilderView', function (require) {
"use strict";

var BasicView = require('web.BasicView');
var core = require('web.core');
var view_registry = require('web.view_registry');
    
var BuilderController = require('formio.BuilderController');
var BuilderRenderer = require('formio.BuilderRenderer');

var _lt = core._lt;

var BuilderView = BasicView.extend({
    config: _.extend({}, BasicView.prototype.config, {
        Renderer: BuilderRenderer,
        Controller: BuilderController,
    }),
    display_name: _lt('Builder'),
    icon: 'fa-rocket',
    multi_record: false,
    searchable: false,
    jsLibs: [],
    viewType: 'formio_builder',

    /**
     * @override
     */
    init: function (viewInfo, params) {
        this._super.apply(this, arguments);
        this.loadParams.type = 'record';
    }
});

view_registry.add('formio_builder', BuilderView);
return BuilderView;

});
