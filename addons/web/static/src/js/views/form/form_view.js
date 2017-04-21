odoo.define('web.FormView', function (require) {
"use strict";

var BasicView = require('web.BasicView');
var Context = require('web.Context');
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

        var mode = params.mode || (params.currentId ? 'readonly' : 'edit');
        this.loadParams.type = 'record';
        this.loadParams.parentID = params.parentID;

        this.controllerParams.hasSidebar = params.sidebar;
        this.controllerParams.toolbar = false;
        this.controllerParams.footerToButtons = params.footer_to_buttons;
        if ('action' in params && 'flags' in params.action) {
            this.controllerParams.footerToButtons = params.action.flags.footer_to_buttons;
        }
        var defaultButtons = 'default_buttons' in params ? params.default_buttons : true;
        this.controllerParams.defaultButtons = defaultButtons;
        this.controllerParams.mode = mode;

        this.rendererParams.mode = mode;
        this.model = params.model;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    getController: function (parent) {
        var self = this;
        var defs = [];
        var fields = this.loadParams.fields;

        _.each(self.loadParams.fieldsInfo.form, function (attrs, fieldName) {
            var field = fields[fieldName];
            if (field.type !== 'one2many' && field.type !== 'many2many') {
                return;
            }

            attrs.limit = attrs.mode === "tree" ? 80 : 40;

            if (attrs.Widget.prototype.useSubview && !(attrs.invisible && JSON.parse(attrs.invisible)) && !attrs.views[attrs.mode]) {
                var context = {};
                var regex = /'([a-z]*_view_ref)' *: *'(.*?)'/g;
                var matches;
                while (matches = regex.exec(attrs.context)) {
                    context[matches[1]] = matches[2];
                }
                defs.push(parent.loadViews(
                        field.relation,
                        new Context(context, self.userContext),
                        [[null, attrs.mode === 'tree' ? 'list' : attrs.mode]])
                    .then(function (views) {
                        for (var viewName in views) {
                            attrs.views[viewName] = views[viewName];
                        }
                    }));
            }
        });
        return $.when.apply($, defs).then(this._super.bind(this, parent));
    },
});

return FormView;

});
