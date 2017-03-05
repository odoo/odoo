odoo.define('web.FormView', function (require) {
"use strict";

var BasicView = require('web.BasicView');
var FormRenderer = require('web.FormRenderer');
var FormController = require('web.FormController');
var core = require('web.core');

var _lt = core._lt;

var FormView = BasicView.extend({
    display_name: _lt('Form'),
    icon: 'fa-edit',
    multi_record: false,
    searchable: false,

    config: _.extend({}, BasicView.prototype.config, {
        Renderer: FormRenderer,
        Controller: FormController,
    }),
    init: function (arch, fields, params) {
        this._super.apply(this, arguments);

        var mode = params.mode || (params.currentId ? 'readonly' : 'edit');
        this.loadParams.type = 'record';

        this.controllerParams.hasSidebar = params.sidebar;
        this.controllerParams.toolbar = false;
        this.controllerParams.footerToButtons = params.footer_to_buttons;
        if ('action' in params) {
            this.controllerParams.footerToButtons = params.action.flags.footer_to_buttons;
        }
        var defaultButtons = 'default_buttons' in params ? params.default_buttons : true;
        this.controllerParams.defaultButtons = defaultButtons;
        this.controllerParams.mode = mode;

        this.rendererParams.mode = mode;
        this.model = params.model;
    },
});

return FormView;

});
