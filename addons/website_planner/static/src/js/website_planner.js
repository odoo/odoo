odoo.define('website_planner.planner', function (require) {
'use strict';

var Model = require('web.Model');
var Widget = require('web.Widget');
var planner = require('planner.planner_common');
var website = require('website.website');

var PlannerDialog = planner.PlannerDialog;

planner.PlannerLauncher = Widget.extend({
    template: "PlannerLauncher",
    events: {
        'click .oe_planner_progress': 'toggle_dialog'
    },
    init: function() {
        this._super();
        var self = this;
        self.get_website_planner().then(function(planner) {
            self.planner = planner;
            self.prependTo(window.$('#oe_systray'));
        });
    },
    start: function() {
        this._super.apply(this, arguments);
        this.setup(this.planner);
    },
    get_website_planner: function() {
        return (new Model('planner.planner')).call('get_website_planner', []);
    },
    setup: function() {
        var self = this;
        this.dialog = new PlannerDialog(this, this.planner);
        this.$(".oe_planner_progress").tooltip({html: true, title: this.planner.tooltip_planner, placement: 'bottom', container: 'body', delay: {'show': 700}});
        this.dialog.on("planner_progress_changed", this, function(percent) {
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
PlannerDialog.include({
    prepare_planner_event: function() {
        var self = this;
        this._super.apply(this, arguments);
        self.$el.on("click", ".oe_planner a.hide_planner", function(ev) {
            self.$('#PlannerModal').modal('hide');
        });
    }
});
website.ready().done(function() {
    if($('#oe_systray').length) {
        website.add_template_file('/planner/static/src/xml/planner.xml').then(function() {
            new planner.PlannerLauncher();
        });
    }
});

});

