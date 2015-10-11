odoo.define('web_settings_dashboard', function (require) {
"use strict";

var core = require('web.core');
var Widget = require('web.Widget');
var Model = require('web.Model');
var session = require('web.session');
var PlannerCommon = require('web.planner.common');
var framework = require('web.framework');
var webclient = require('web.web_client');
var PlannerDialog = PlannerCommon.PlannerDialog;

var QWeb = core.qweb;
var _t = core._t;

var Dashboard = Widget.extend({
    template: 'DashboardMain',

    events: {
        'click .o_browse_apps': 'on_new_apps',
    },

    start: function(){
        return this.load(['apps', 'invitations', 'planner', 'share'])
    },

    load: function(dashboards){
        var self = this;
        var loading_done = new $.Deferred();
        session.rpc("/web_settings_dashboard/data", {}).then(function (data) {
            // Load each dashboard
            var all_dashboards_defs = []
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
        this.$('.o_web_settings_dashboard_apps').append(QWeb.render("DashboardApps", data['apps']));
    },

    load_share: function(data){
        return new DashboardShare(this, {}).replace(this.$('.o_web_settings_dashboard_share'));
    },

    load_invitations: function(data){
        return new DashboardInvitations(this, data['users_info']).replace(this.$('.o_web_settings_dashboard_invitations'));
    },

    load_planner: function(data){
        return  new DashboardPlanner(this, data['planner']).replace(this.$('.o_web_settings_dashboard_planner'));
    },

    on_new_apps: function(){
        this.do_action('base.open_module_tree');
    }
});

var DashboardInvitations = Widget.extend({
    template: 'DashboardInvitations',
    events: {
        'click .o_web_settings_dashboard_invitations': 'send_invitations',
        'click .o_web_settings_dashboard_access_rights': 'on_access_rights_clicked',
        'click .o_web_settings_dashboard_user': 'on_user_clicked',
    },
    init: function(parent, data){
        this.data = data;
        this.parent = parent;
        return this._super.apply(this, arguments);
    },
    send_invitations: function(e){
        var self = this;
        var $target = $(e.currentTarget);
        var user_emails =  _.filter(this.$('#user_emails').val().split(/[\n, ]/), function(email){
            return email != "";
        });
        var re = /^([\w-]+(?:\.[\w-]+)*)@((?:[\w-]+\.)*\w[\w-]{0,66})\.([a-z]{2,6}(?:\.[a-z]{2})?)$/i;
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
                    self.$('.o_web_settings_dashboard_invitations').prop('disabled', false);
                    self.$('i.fa-cog').addClass('hidden');
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
        }
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
        'click .o_web_settings_dashboard_progress_title,.progress': 'on_planner_clicked',
    },

    init: function(parent, data){
        this.data = data;
        this.parent = parent;
        this.planner_by_menu = {};
        this._super.apply(this, arguments);
    },

    willStart:function(){
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
        this.planners = _.sortBy(this.planners, function(planner){return (planner.progress == 100) + planner.name});
    },

    on_planner_clicked: function(e){

        var menu_id = $(e.currentTarget).attr('data-menu-id');
        // Setup the planner if we didn't do it yet
        if (this.planner && this.planner.menu_id[0] == menu_id) {
            this.dialog.$el.modal('show');
        }
        else {
            this.setup_planner(menu_id);
        }
    },

    setup_planner: function(menu_id){
        var self = this;
        this.planner = self.planner_by_menu[menu_id];
        if (this.dialog) {
            this.dialog.destroy()
        }
        this.dialog = new PlannerDialog(this, this.planner);
        this.dialog.on("planner_progress_changed", this, function(percent) {
            self.planner.progress = percent;
            self.update_planner_progress();
        });
        this.dialog.appendTo(webclient.$el).then(function() {
            self.dialog.$el.modal('show');
        });
    }
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
        this.share_url = 'http://www.odoo.com/';
        this.share_text = encodeURIComponent("Discover #Odoo - awesome open source business apps. https://www.odoo.com");
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
