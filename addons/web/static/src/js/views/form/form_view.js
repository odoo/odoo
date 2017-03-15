odoo.define('web.FormView', function (require) {
"use strict";

var BasicView = require('web.BasicView');
var FormRenderer = require('web.FormRenderer');
var FormController = require('web.FormController');
var Context = require('web.Context');
var config = require('web.config');
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
    /**
     * @override
     */
    init: function (arch, fields, params) {
        this._super.apply(this, arguments);

        var mode = params.mode || (params.currentId ? 'readonly' : 'edit');
        this.loadParams.type = 'record';
        this.loadParams.parentID = params.parentID;

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
    /**
     * @override
     */
    getController: function (parent) {
        var self = this;
        var defs = [];
        var fields = this.loadParams.fields;

        _.each(self.loadParams.fieldAttrs, function (attrs, fieldName) {
            var field = fields[fieldName];
            if (field.type !== 'one2many' && field.type !== 'many2many') {
                return;
            }

            if (attrs.Widget.prototype.useSubview && !(attrs.invisible && JSON.parse(attrs.invisible))) {
                var mode = attrs.mode;
                if (!mode) {
                    if (field.views.tree && field.views.kanban) {
                        mode = 'tree';
                    } else if (!field.views.tree && field.views.kanban) {
                        mode = 'kanban';
                    } else {
                        mode = 'tree,kanban';
                    }
                }
                if (mode.indexOf(',') !== -1) {
                    mode = config.device.size_class !== config.device.SIZES.XS ? 'tree' : 'kanban';
                }
                if (field.views[mode]) {
                    field.relatedFields = field.views[mode].fields;
                    field.fieldAttrs = field.views[mode].fieldAttrs;
                    field.limit = mode === "tree" ? 80 : 40;
                    return;
                }
                defs.push(parent.loadViews(
                        field.relation,
                        new Context(self.loadParams.context),
                        [[null, mode === 'tree' ? 'list' : mode]],
                        {})
                    .then(function (views) {
                        for (var viewName in views) {
                            var view = views[viewName];
                            var fieldView = self._processFieldsView(view.arch, view.fields);
                            field.views[viewName === 'list' ? 'tree' : viewName] = view;
                            field.relatedFields = fieldView.view_fields;
                            field.fieldAttrs = fieldView.fieldAttrs;
                            view.fieldAttrs = fieldView.fieldAttrs;
                        }
                    }));
            }
        });
        return $.when.apply($, defs).then(this._super.bind(this, parent));
    },
});

return FormView;

});
