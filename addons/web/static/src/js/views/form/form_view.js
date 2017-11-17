odoo.define('web.FormView', function (require) {
"use strict";

var BasicView = require('web.BasicView');
var core = require('web.core');
var FormController = require('web.FormController');
var FormRenderer = require('web.FormRenderer');

var _lt = core._lt;

var FormView = BasicView.extend({
    config: _.extend({}, BasicView.prototype.config, {
        Renderer: FormRenderer,
        Controller: FormController,
    }),
    display_name: _lt('Form'),
    icon: 'fa-edit',
    multi_record: false,
    searchable: false,
    viewType: 'form',
    /**
     * @override
     */
    init: function (viewInfo, params) {
        this._super.apply(this, arguments);

        var mode = params.mode || params.context.form_view_initial_mode ||
                   (params.currentId ? 'readonly' : 'edit');
        this.loadParams.type = 'record';

        this.controllerParams.disableAutofocus = params.disable_autofocus;
        this.controllerParams.hasSidebar = params.hasSidebar;
        this.controllerParams.toolbarActions = viewInfo.toolbar;
        this.controllerParams.footerToButtons = params.footerToButtons;
        if ('action' in params && 'flags' in params.action) {
            this.controllerParams.footerToButtons = params.action.flags.footerToButtons;
        }
        var defaultButtons = 'default_buttons' in params ? params.default_buttons : true;
        this.controllerParams.defaultButtons = defaultButtons;
        this.controllerParams.mode = mode;

        this.rendererParams.mode = mode;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    getController: function (parent) {
        return this._loadSubviews(parent).then(this._super.bind(this, parent));
    },
});

return FormView;

});
