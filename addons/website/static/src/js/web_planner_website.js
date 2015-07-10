odoo.define('web.planner.website', function (require) {
'use strict';

var ajax = require('web.ajax');
var core = require('web.core');
var Model = require('web.Model');
var Widget = require('web.Widget');
var planner = require('web.planner.common');
var base = require('web_editor.base');

var qweb = core.qweb;

var PlannerDialog = planner.PlannerDialog;

planner.WebistePlannerLauncher = Widget.extend({
    template: "PlannerLauncher",
    events: {
        'click .o_planner_progress': 'toggle_dialog'
    },
    start: function() {
        var self = this;
        this._super.apply(this, arguments);
        return this.get_website_planner().then(function(planner) {
            if (planner.length) {
                self.planner = planner[0];
                self.planner.data = $.parseJSON(planner[0].data) || {};
                self.setup();
            }
        });
    },
    get_website_planner: function() {
        return (new Model('web.planner')).call('search_read', [[['planner_application', '=', 'planner_website']]]);
    },
    setup: function() {
        var self = this;
        this.dialog = new PlannerDialog(this, this.planner);
        this.$(".o_planner_progress").tooltip({html: true, title: this.planner.tooltip_planner, placement: 'bottom', container: 'body', delay: {'show': 700}});
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
        self.$el.on("click", ".o_planner a.o_planner_hide", function(ev) {
            self.$('#PlannerModal').modal('hide');
        });
    }
});

base.dom_ready.done(function() {
    if($('#oe_systray').length) {
        ajax.loadXML('/web_planner/static/src/xml/web_planner.xml', qweb).then(function() {
            new planner.WebistePlannerLauncher().prependTo($('#oe_systray'));
        });
    }
});

});
