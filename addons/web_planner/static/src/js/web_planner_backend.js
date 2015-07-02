odoo.define('web.planner', function (require) {
"use strict";

var core = require('web.core');
var Model = require('web.Model');
var SystrayMenu = require('web.SystrayMenu');
var Widget = require('web.Widget');
var planner = require('web.planner.common');
var WebClient = require('web.WebClient');

var PlannerDialog = planner.PlannerDialog;

var PlannerLauncher = Widget.extend({
    template: "PlannerLauncher",
    events: {
        'click .o_planner_progress': 'toggle_dialog'
    },
    init: function(parent) {
        this._super(parent);
        this.planner_by_menu = {};
        this.webclient = parent.getParent();
        this.need_reflow = false;
    },
    start: function() {
        var self = this;
        self._super();

        self.webclient.menu.on("open_menu", self, self.on_menu_clicked);
        self.$el.hide();  // hidden by default
        return self.fetch_application_planner().done(function(apps) {
            self.planner_apps = apps;
            return apps;
        });
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
    on_menu_clicked: function(id, $clicked_menu) {
        var menu_id = $clicked_menu.parents('.oe_secondary_menu').data('menu-parent') || 0; // find top menu id
        if (_.contains(_.keys(this.planner_apps), menu_id.toString())) {
            this.setup(this.planner_apps[menu_id]);
            this.need_reflow = true;
        } else {
            this.$el.hide();
            this.hide_dialog();
            this.need_reflow = true;
        }
        if (this.need_reflow) {
            core.bus.trigger('resize');
            this.need_reflow = false;
        }
    },
    setup: function(planner){
        var self = this;
        var webclient = this.findAncestor(function (a) {
            return a instanceof WebClient;
        });

        this.planner = planner;
        if (this.dialog) {
            this.dialog.destroy();
        }
        this.dialog = new PlannerDialog(this, planner);
        this.dialog.$el.remove();
        this.dialog.appendTo(webclient.$el);
        this.$(".o_planner_progress").tooltip({html: true, title: this.planner.tooltip_planner, placement: 'bottom', delay: {'show': 500}});
        this.dialog.on("planner_progress_changed", this, function(percent){
            self.update_parent_progress_bar(percent);
        });
    },
    // event
    update_parent_progress_bar: function(percent) {
        if (percent == 100) {
            this.$(".progress").hide();
        } else {
            this.$(".progress").show();
        }
        this.$el.show();
        this.$(".progress-bar").css('width', percent+"%");
    },
    hide_dialog: function() {
        if (this.dialog) {
            this.dialog.$el.hide();
        }
    },
    toggle_dialog: function() {
        this.dialog.$el.toggle();
    }
});

// add planner launcher to the systray
// if it is empty, it won't be display. Then, each time a top menu is clicked
// a planner will be given to the launcher. The launcher will appears if the
// given planner is not null.
SystrayMenu.Items.push(PlannerLauncher);

return {
    PlannerLauncher: PlannerLauncher,
};

});
