odoo.define('web.planner', function (require) {
"use strict";

var core = require('web.core');
var Dialog = require('web.Dialog');
var Model = require('web.Model');
var SystrayMenu = require('web.SystrayMenu');
var Widget = require('web.Widget');
var planner = require('web.planner.common');
var webclient = require('web.web_client');

var QWeb = core.qweb;
var _t = core._t;
var PlannerDialog = planner.PlannerDialog;

var PlannerLauncher = Widget.extend({
    template: "PlannerLauncher",
    init: function(parent) {
        this._super(parent);
        this.planner_by_menu = {};
        this.need_reflow = false;
    },
    start: function() {
        var self = this;
        core.bus.on("change_menu_section", self, self.on_menu_clicked);

        var res =  self._super.apply(this, arguments).then(function() {
            self.$el.on('click', self, self.show_dialog.bind(self));
            return self.fetch_application_planner();
        }).then(function(apps) {
            self.$('.progress').tooltip({html: true, placement: 'bottom', delay: {'show': 500}});
            self.planner_apps = apps;
            return apps;
        });
        return res;
    },
    fetch_application_planner: function() {
        var self = this;
        var def = $.Deferred();
        if (!_.isEmpty(this.planner_by_menu)) {
            def.resolve(self.planner_by_menu);
        }else{
            (new Model('web.planner')).query().all().then(function(res) {
                _.each(res, function(planner){
                    self.planner_by_menu[planner.menu_id[0]] = planner;
                    self.planner_by_menu[planner.menu_id[0]].data = $.parseJSON(self.planner_by_menu[planner.menu_id[0]].data) || {};
                });
                def.resolve(self.planner_by_menu);
            }).fail(function() {def.reject();});
        }
        return def;
    },
    on_menu_clicked: function(menu_id) {
        if (_.contains(_.keys(this.planner_apps), menu_id.toString())) {
            this.setup(this.planner_apps[menu_id]);
            this.need_reflow = true;
        } else {
            this.$el.hide();
            this.need_reflow = true;
        }
        if (this.need_reflow) {
            core.bus.trigger('resize');
            this.need_reflow = false;
        }

        if (this.dialog) {
            this.dialog.$el.modal('hide');
            this.dialog.$el.detach();
        }
    },
    setup: function(planner) {
        var self = this;

        this.planner = planner;
        if (this.dialog) {
            this.dialog.$el.modal('hide');
            this.dialog.destroy();
        }
        this.dialog = new PlannerDialog(this, planner);
        this.dialog.appendTo($('<div>'));

        this.$('.progress').attr('data-original-title', this.planner.tooltip_planner);
        this.$el.filter('.o_planner_help').find('.o_planner_link').show();

        this.dialog.on("planner_progress_changed", this, function(percent){
            self.update_parent_progress_bar(percent);
        });
    },
    update_parent_progress_bar: function(percent) {
        if (percent == 100) {
            this.$(".progress").hide();
        } else {
            this.$(".progress").show();
        }
        this.$el.show();
        this.$(".progress-bar").css('width', percent+"%");
    },
    show_dialog: function() {
        this.dialog.$el.appendTo(webclient.$el);
        this.dialog.$el.modal('show');
    },
});

SystrayMenu.Items.push(PlannerLauncher);

return {
    PlannerLauncher: PlannerLauncher,
};

});

