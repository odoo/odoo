(function() {

    "use strict";

    var instance = openerp;

    instance.planner.PlannerLauncher = instance.web.Widget.extend({
        template: "PlannerLauncher",
        events: {
            'click .oe_planner_progress': 'toggle_dialog'
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
                (new instance.web.Model('planner.planner')).query().all().then(function(res) {
                    _.each(res, function(planner){
                        self.planner_by_menu[planner.menu_id[0]] = planner;
                        self.planner_by_menu[planner.menu_id[0]].data = jQuery.parseJSON(self.planner_by_menu[planner.menu_id[0]].data) || {};
                    });
                    def.resolve(self.planner_by_menu);
                }).fail(function() {def.reject();});
            }
            return def;
        },
        on_menu_clicked: function(id, $clicked_menu) {
            var menu_id = $clicked_menu.parents('.oe_secondary_menu').data('menu-parent') || 0; // find top menu id
            if (_.contains(_.keys(this.planner_apps), menu_id.toString())) {
                this.$el.show();
                this.setup(this.planner_apps[menu_id]);
                this.need_reflow = true;
            } else {
                if (this.$el.is(":visible")) {
                    this.$el.hide();
                    this.need_reflow = true;
                }
            }
            if (this.need_reflow) {
                this.webclient.menu.reflow();
                this.need_reflow = false;
            }
        },
        setup: function(planner){
            var self = this;
            this.planner = planner;
            this.dialog = new instance.planner.PlannerDialog(this, planner);
            this.$(".oe_planner_progress").tooltip({html: true, title: this.planner.tooltip_planner, placement: 'bottom', delay: {'show': 500}});
            this.dialog.on("planner_progress_changed", this, function(percent){
                self.update_parent_progress_bar(percent);
            });
            this.dialog.appendTo(document.body);
        },
        // event
        update_parent_progress_bar: function(percent) {
            this.$(".progress-bar").css('width', percent+"%");
        },
        toggle_dialog: function() {
            this.dialog.$('#PlannerModal').modal('toggle');
        }
    });

    // add planner launcher to the systray
    // if it is empty, it won't be display. Then, each time a top menu is clicked
    // a planner will be given to the launcher. The launcher will appears if the
    // given planner is not null.
    openerp.web.SystrayItems.push(instance.planner.PlannerLauncher);

})();