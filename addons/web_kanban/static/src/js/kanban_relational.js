odoo.define('web_kanban.Many2ManyKanbanView', function (require) {
"use strict";

var common = require('web.form_common');
var core = require('web.core');
var data = require('web.data');
var KanbanView = require('web_kanban.KanbanView');

var _t = core._t;

var X2ManyKanbanView = KanbanView.extend({
    render_pager: function($node, options) {
        options = _.extend(options || {}, {
            single_page_hidden: true,
        });
        this._super($node, options);
    },
});

var One2ManyKanbanView = X2ManyKanbanView.extend({
    add_record: function() {
        var self = this;
        new common.FormViewDialog(this, {
            res_model: self.x2m.field.relation,
            domain: self.x2m.build_domain(),
            context: self.x2m.build_context(),
            title: _t("Create: ") + self.x2m.string,
            initial_view: "form",
            alternative_form_view: self.x2m.field.views ? self.x2m.field.views.form : undefined,
            create_function: function(data, options) {
                return self.x2m.data_create(data, options);
            },
            read_function: function(ids, fields, options) {
                return self.x2m.data_read(ids, fields, options);
            },
            parent_view: self.x2m.view,
            child_name: self.x2m.name,
            form_view_options: {'not_interactible_on_create':true},
            on_selected: function() {
                self.x2m.reload_current_view();
            }
        }).open();
    },
});

var Many2ManyKanbanView = X2ManyKanbanView.extend({
    add_record: function() {
        var self = this;
        new common.SelectCreateDialog(this, {
            res_model: this.x2m.field.relation,
            domain: new data.CompoundDomain(this.x2m.build_domain(), ["!", ["id", "in", this.dataset.ids]]),
            context: this.x2m.build_context(),
            title: _t("Add: ") + this.x2m.string,
            on_selected: function(element_ids) {
                return self.x2m.data_link_multi(element_ids).then(function() {
                    self.x2m.reload_current_view();
                });
            }
        }).open();
    },
    open_record: function(event) {
        var self = this;
        new common.FormViewDialog(this, {
            res_model: this.x2m.field.relation,
            res_id: event.data.id,
            context: this.x2m.build_context(),
            title: _t("Open: ") + this.x2m.string,
            write_function: function(id, data, options) {
                return self.x2m.data_update(id, data, options).done(function() {
                    self.x2m.reload_current_view();
                });
            },
            alternative_form_view: this.x2m.field.views ? this.x2m.field.views.form : undefined,
            parent_view: this.x2m.view,
            child_name: this.x2m.name,
            read_function: function(ids, fields, options) {
                return self.x2m.data_read(ids, fields, options);
            },
            form_view_options: {'not_interactible_on_create': true},
            readonly: !this.is_action_enabled('edit') || this.x2m.get("effective_readonly")
        }).open();
    },
});

core.view_registry.add('one2many_kanban', One2ManyKanbanView);
core.view_registry.add('many2many_kanban', Many2ManyKanbanView);

});

