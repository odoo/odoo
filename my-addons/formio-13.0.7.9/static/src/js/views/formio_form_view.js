odoo.define('formio.FormView', function (require) {
"use strict";

var BasicView = require('web.BasicView');
var core = require('web.core');
var view_registry = require('web.view_registry');
    
var FormController = require('formio.FormController');
var FormRenderer = require('formio.FormRenderer');

var _lt = core._lt;

var FormView = BasicView.extend({
    config: _.extend({}, BasicView.prototype.config, {
        Renderer: FormRenderer,
        Controller: FormController,
    }),
    display_name: _lt('Form'),
    icon: 'fa-rocket',
    multi_record: false,
    searchable: false,
    jsLibs: [],
    viewType: 'formio_form',
    /**
     * @override
     */
    init: function (viewInfo, params) {
        this._super.apply(this, arguments);
        this.loadParams.type = 'record';
    }
});

view_registry.add('formio_form', FormView);
return FormView;

});
