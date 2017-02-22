odoo.define('web_settings_dashboard', function (require) {
"use strict";

var core = require('web.core');
var framework = require('web.framework');
var Model = require('web.Model');
var PlannerCommon = require('web.planner.common');
var PlannerDialog = PlannerCommon.PlannerDialog;
var Widget = require('web.Widget');

var QWeb = core.qweb;
var _t = core._t;

var Dashboard = Widget.extend({
    template: 'DashboardMain',

    init: function(){
        this.all_dashboards = ['apps', 'invitations', 'planner', 'share'];
        return this._super.apply(this, arguments);
    },

    start: function(){
        return this.load(this.all_dashboards);
    },

    load: function(dashboards){
        var self = this;
        var loading_done = new $.Deferred();
        this.performRPC("/web_settings_dashboard/data", {}).then(function (data) {
            // Load each dashboard
            var all_dashboards_defs = [];
            _.each(dashboards, function(dashboard) {
                var dashboard_def = self['load_' + dashboard](data);
                if (dashboard_def) {
                    all_dashboards_defs.push(dashboard_def);
                }
            });

            // Resolve loading_done when all dashboards defs are resolved
            $.when.apply($, all_dashboards_defs).then(function() {
                loading_done.resolve();
            });
        });
        return loading_done;
    },

    load_apps: function(data){
        return  new DashboardApps(this, data.apps).replace(this.$('.o_web_settings_dashboard_apps'));
    },

    load_share: function(data){
        return new DashboardShare(this, data.share).replace(this.$('.o_web_settings_dashboard_share'));
    },

    load_invitations: function(data){
        return new DashboardInvitations(this, data.users_info).replace(this.$('.o_web_settings_dashboard_invitations'));
    },

    load_planner: function(data){
        return  new DashboardPlanner(this, data.planner).replace(this.$('.o_web_settings_dashboard_planner'));
    },
});

var DashboardInvitations = Widget.extend({
    template: 'DashboardInvitations',
    events: {
        'click .o_web_settings_dashboard_invitations': 'send_invitations',
        'click .o_web_settings_dashboard_access_rights': 'on_access_rights_clicked',
        'click .o_web_settings_dashboard_user': 'on_user_clicked',
        'click .o_web_settings_dashboard_more': 'on_more',
    },
    init: function(parent, data){
        this.data = data;
        this.parent = parent;
        return this._super.apply(this, arguments);
    },
    send_invitations: function(e){
        var self = this;
        var $target = $(e.currentTarget);
        var user_emails =  _.filter($(e.delegateTarget).find('#user_emails').val().split(/[\n, ]/), function(email){
            return email !== "";
        });
        var re = /^([\w-]+(?:\.[\w-]+)*)@((?:[\w-]+\.)*\w[\w-]{0,66})\.([a-z]{2,63}(?:\.[a-z]{2})?)$/i;
        var is_valid_emails = _.every(user_emails, function(email) {
            return re.test(email);
        });
        if (is_valid_emails) {
            // Disable button
            $target.prop('disabled', true);
            $target.find('i.fa-cog').removeClass('hidden');
            // Try to create user accountst
            new Model("res.users")
                .call("web_dashboard_create_users", [user_emails])
                .then(function() {
                    self.reload();
                })
                .always(function() {
                    // Re-enable button
                    $(e.delegateTarget).find('.o_web_settings_dashboard_invitations').prop('disabled', false);
                    $(e.delegateTarget).find('i.fa-cog').addClass('hidden');
                });

        }
        else {
            this.do_warn(_t("Please provide valid email addresses"), "");
        }
    },
    on_access_rights_clicked: function (e) {
        var self = this;
        e.preventDefault();
        this.do_action('base.action_res_users', {
            on_reverse_breadcrumb: function(){ return self.reload();}
        });
    },
    on_user_clicked: function (e) {
        var self = this;
        e.preventDefault();
        var user_id = $(e.currentTarget).data('user-id');
        var action = {
            type: 'ir.actions.act_window',
            view_type: 'form',
            view_mode: 'form',
            res_model: 'res.users',
            views: [[this.data.user_form_view_id, 'form']],
            res_id: user_id,
        };
        this.do_action(action,{
            on_reverse_breadcrumb: function(){ return self.reload();}
        });
    },
    on_more: function(e) {
        var self = this;
        e.preventDefault();
        var action = {
            type: 'ir.actions.act_window',
            view_type: 'form',
            view_mode: 'tree,form',
            res_model: 'res.users',
            domain: [['log_ids', '=', false]],
            views: [[false, 'list'], [false, 'form']],
        };
        this.do_action(action,{
            on_reverse_breadcrumb: function(){ return self.reload();}
        });
    },
    reload:function(){
        return this.parent.load(['invitations']);
    },
});

var DashboardPlanner = Widget.extend({

    template: 'DashboardPlanner',

    events: {
        'click .o_web_settings_dashboard_planner_progress_bar': 'on_planner_clicked',
    },

    init: function(parent, data){
        this.data = data;
        this.parent = parent;
        this.planner_by_menu = {};
        this._super.apply(this, arguments);
    },

    willStart: function () {
        var self = this;
        return new Model('web.planner').query().all().then(function(res) {
            self.planners = res;
            _.each(self.planners, function(planner) {
                self.planner_by_menu[planner.menu_id[0]] = planner;
                self.planner_by_menu[planner.menu_id[0]].data = $.parseJSON(planner.data) || {};
            });
            self.set_overall_progress();
        });
    },

    update_planner_progress: function(){
        this.set_overall_progress();
        this.$('.o_web_settings_dashboard_planners_list').replaceWith(
            QWeb.render("DashboardPlanner.PlannersList", {'planners': this.planners})
        );
    },

    set_overall_progress: function(){
        var self = this;
        this.sort_planners_list();
        var average = _.reduce(self.planners, function(memo, planner) {
            return planner.progress + memo;
        }, 0) / (self.planners.length || 1);
        self.overall_progress = Math.floor(average);
        self.$('.o_web_settings_dashboard_planner_overall_progress').text(self.overall_progress);
    },

    sort_planners_list: function(){
        // sort planners alphabetically but with fully completed planners at the end:
        this.planners = _.sortBy(this.planners, function(planner){return (planner.progress >= 100) + planner.name;});
    },

    on_planner_clicked: function (e) {
        var menu_id = $(e.currentTarget).attr('data-menu-id');
        this.planner = this.planner_by_menu[menu_id];

        this.dialog = new PlannerDialog(this, undefined, this.planner);
        this.dialog.on("planner_progress_changed", this, function(percent) {
            this.planner.progress = percent;
            this.update_planner_progress();
        });
        this.dialog.open();
    },
});

var DashboardApps = Widget.extend({

    template: 'DashboardApps',

    events: {
        'click .o_browse_apps': 'on_new_apps',
        'click .o_confirm_upgrade': 'confirm_upgrade',
    },

    init: function(parent, data){
        this.data = data;
        this.parent = parent;
        return this._super.apply(this, arguments);
    },

    start: function() {
        this._super.apply(this, arguments);
        if (odoo.db_info && _.last(odoo.db_info.server_version_info) !== 'e') {
            $(QWeb.render("DashboardEnterprise")).appendTo(this.$el);
        }
    },

    on_new_apps: function(){
        this.do_action('base.open_module_tree');
    },

    confirm_upgrade: function() {
        framework.redirect("https://www.odoo.com/odoo-enterprise/upgrade?num_users=" + (this.data.enterprise_users || 1));
    },
});

var DashboardShare = Widget.extend({
    template: 'DashboardShare',

    events: {
        'click .tw_share': 'share_twitter',
        'click .fb_share': 'share_facebook',
        'click .li_share': 'share_linkedin',
    },

    init: function(parent, data){
        this.data = data;
        this.parent = parent;
        this.share_url = 'https://www.odoo.com';
        this.share_text = encodeURIComponent("I am using #Odoo - Awesome open source business apps.");
    },

    share_twitter: function(){
        var popup_url = _.str.sprintf( 'https://twitter.com/intent/tweet?tw_p=tweetbutton&text=%s %s',this.share_text,this.share_url);
        this.sharer(popup_url);
    },

    share_facebook: function(){
        var popup_url = _.str.sprintf('https://www.facebook.com/sharer/sharer.php?u=%s', encodeURIComponent(this.share_url));
        this.sharer(popup_url);
    },

    share_linkedin: function(){
        var popup_url = _.str.sprintf('http://www.linkedin.com/shareArticle?mini=true&url=%s&title=I am using odoo&summary=%s&source=www.odoo.com', encodeURIComponent(this.share_url), this.share_text);
        this.sharer(popup_url);
    },

    sharer: function(popup_url){
        window.open(
            popup_url,
            'Share Dialog',
            'width=600,height=400'); // We have to add a size otherwise the window pops in a new tab
    }
});

core.action_registry.add('web_settings_dashboard.main', Dashboard);

return {
    Dashboard: Dashboard,
    DashboardInvitations: DashboardInvitations,
    DashboardPlanner: DashboardPlanner,
    DashboardShare: DashboardShare,
};

});
