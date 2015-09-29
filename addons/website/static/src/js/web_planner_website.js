odoo.define('web.planner.website', function (require) {
'use strict';

var ajax = require('web.ajax');
var core = require('web.core');
var Model = require('web.Model');
var Widget = require('web.Widget');
var planner = require('web.planner.common');
require('web_editor.base');  // wait for implicit dependencies to load

var qweb = core.qweb;

if(!$('#oe_systray').length) {
    return $.Deferred().reject("DOM doesn't contain '#oe_systray'");
}

var WebsitePlannerLauncher = Widget.extend(planner.PlannerHelpMixin, {
    template: "PlannerLauncher",
    start: function() {
        var self = this;
        var res = this._super.apply(this, arguments);
        return res.then(this.get_website_planner.bind(this)).then(function(planner) {
            self.$el.filter('.o_planner_systray').on('click', self, self.show_dialog.bind(self));
            self.$el.filter('.o_planner_help').on('click', '.dropdown-menu li a[data-menu]', self.on_menu_help);
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
        this.dialog = new planner.PlannerDialog(this, this.planner);
        this.dialog.appendTo($('<div>'));
        this.$(".progress").tooltip({html: true, title: this.planner.tooltip_planner, placement: 'bottom', container: 'body', delay: {'show': 700}});
        this.dialog.on("planner_progress_changed", this, function(percent) {
            self.update_parent_progress_bar(percent);
        });
    },
    update_parent_progress_bar: function(percent) {
        this.$(".progress-bar").css('width', percent+"%");
    },
    show_dialog: function() {
        this.dialog.$el.appendTo(document.body);
        this.dialog.$el.modal('show');
    },
});

return ajax.loadXML('/web_planner/static/src/xml/web_planner.xml', qweb).then(function() {
            var websitePlannerLauncher = new WebsitePlannerLauncher();
            websitePlannerLauncher.prependTo($('#oe_systray'));
        });

});

