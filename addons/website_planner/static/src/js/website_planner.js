(function(){
    "use strict";

    var instance = openerp;

    instance.planner.PlannerLauncher = openerp.Widget.extend({
        template: "PlannerLauncher",
        events: {
            'click .oe_planner_progress': 'toggle_dialog'
        },
        init: function() {
            this._super();
            var self = this;
            self.get_website_planner().then(function(planner) {
                self.planner = planner;
                //Add Planner Launcher to systray
                self.prependTo(window.$('#oe_systray'));
            });
        },
        start: function() {
            this._super.apply(this, arguments);
            this.setup(this.planner);
        },
        get_website_planner: function() {
            return instance.jsonRpc('/planner/website_planner', 'call', {});
        },
        setup: function() {
            var self = this;
            this.dialog = new instance.planner.PlannerDialog(this, this.planner);
            this.$(".oe_planner_progress").tooltip({html: true, title: this.planner.tooltip_planner, placement: 'bottom', delay: {'show': 500}});
            this.dialog.on("planner_progress_changed", this, function(percent){
                self.update_parent_progress_bar(percent);
            });
            this.dialog.appendTo(document.body);
        },
        update_parent_progress_bar: function(percent) {
            this.$(".progress-bar").css('width', percent+"%");
        },
        toggle_dialog: function() {
            this.dialog.$('#PlannerModal').modal('toggle');
        },
    });

    //TODO DKA: Remove Singletone Lazy Layer
    instance.website.add_template_file('/planner/static/src/xml/planner.xml').then(function(){
       new instance.planner.PlannerLauncher();
    });

})();
