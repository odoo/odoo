odoo.define('web.dashboard', function (require) {
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
        'click .o_install_new_apps': 'new_apps',
    },
    start: function(){
        //Add 'gift' instead of 'share' to enable amazone dashboard
        return this.load(['apps', 'invitations', 'planner', 'share'])
    },
    load: function(dashboards){
        var self = this;
        var loading_done = new $.Deferred();
        session.rpc("/dashboard/info", {}).then(function (data) {
            var deferred_promises = []
            _.each(dashboards, function(dashboard) {
                var def = self[dashboard](data);
                if (def) {
                    deferred_promises.push(def);
                }
                framework.unblockUI();
            });
            $.when.apply($, deferred_promises)
                .then(function() {
                    loading_done.resolve();
                });
        });
        return loading_done;
    },
    apps: function(data){
        this.$('.o_web_dashboard_apps').append(QWeb.render("DashboardApps", data['apps']));
    },
    share: function(data){
        return new DashboardShare(this, {}).replace(this.$('.o_web_dashboard_share'));
    },
    invitations: function(data){
        return new DashboardInvitations(this, data['users_info']).replace(this.$('.o_web_dashboard_invitations'));
    },
    planner: function(data){
        return  new DashboardPlanner(this, data['planner']).replace(this.$('.o_web_dashboard_planner'));
    },
    gift: function(data){
        return new DashboardGift(this, data['gift']).replace(this.$('.o_web_dashboard_gift'));
    },
    new_apps: function(){
        this.do_action('base.open_module_tree', {
            'additional_context': {'search_default_app': 1, 'search_default_not_installed': 1}
        });
    }
});

var DashboardInvitations = Widget.extend({
    template: 'DashboardInvitations',
    events: {
        'click .o_send_invitations': 'send_invitations',
        'click .optional_message_toggler': 'optional_message_toggler',
        'click .user': 'on_user_clicked',
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
        var optional_message = this.$('#optional_message').val();
        if(is_valid_emails){
            $target.prop('disabled', true);
            $target.find('i.fa-cog').removeClass('hidden');
            new Model("res.users")
                .call("web_dashboard_create_users", [user_emails, optional_message])
                .then(function (result) {
                    self.reload();
                });

        }else{
            this.do_warn(_t("Please provide valid email addresses"), "");
        }
    },
    on_user_clicked: function (event) {
        var self = this;
        var user_id = $(event.target).data('user-id');
        var action = {
            type: 'ir.actions.act_window',
            view_type: 'form',
            view_mode: 'form',
            res_model: 'res.users',
            views: [[this.data.user_form_id, 'form']],
            res_id: user_id,
        }
        this.do_action(action,{
            on_reverse_breadcrumb: function(){ return self.reload();}
        });
    },
    reload:function(){
        return this.parent.load(['invitations']);
    },
    optional_message_toggler: function(){
        this.$('.optional_message_toggler').remove();
        this.$('textarea.optional_message').slideToggle("fast");
    }
});

var DashboardPlanner = Widget.extend({
    template: 'DashboardPlanner',
    events: {
        'click .o_progress_title,.progress': 'on_planner_clicked',
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
                self.planner_by_menu[planner.menu_id[0]].data = $.parseJSON(self.planner_by_menu[planner.menu_id[0]].data) || {};
            });
            self.set_overall_progress();
        });
    },
    update_planner_progress: function(){
        this.set_overall_progress();
        this.$('.o_dashboard_planners_list').replaceWith(
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
        self.$('.o_dashboard_planner_overall_progress').text(self.overall_progress);
    },
    sort_planners_list: function(){
        /* sorted planner in such way so,
            - partially completed planners displayed first(sorted by name)
            - fully completed planners displayed at the end
        */
        this.planners = _.sortBy(this.planners, function(planner){ return (planner.progress == 100) ? "zz" + planner.name : planner.name});
    },
    on_planner_clicked: function(e){
        var menu_id = $(e.currentTarget).attr('data-menu-id');
        if (this.planner && this.planner.menu_id[0] == menu_id) {
             this.dialog.do_show();
        }else{
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
            self.dialog.do_show();
        });
    }
});

var DashboardGift = Widget.extend({
    template: 'DashboardGift',
    events: {
        'click .tw_share': 'share_twitter',
        'click .fb_share': 'share_facebook',
        'click .li_share': 'share_linkedin',
    },
    init: function(parent, data){
        this.data = data;
        this.parent = parent;
        this.share_url = _.str.sprintf('http://www.odoo.com/?referral=%s', this.data.user_email);
        this.share_text = encodeURIComponent("#IamUsingOdoo, an Open-Source Web App that manages my Sales, Projects, Accounting, Website, Warehouse, Shop and more");
        var ZeroClipboard = window.ZeroClipboard;
        ZeroClipboard.config({swfPath: location.origin + "/web/static/lib/zeroclipboard/ZeroClipboard.swf" });
        return this._super.apply(this, arguments);
    },
    start: function(){
        var self = this;
        return $.when(this._super()).then(function() {
            var client = new ZeroClipboard(self.$('.o_dashboard_sharearea'));
            client.on("ready", function(readyEvent) {
                client.on("aftercopy", function(event) {
                    $(event.target).hide();
                    self.$('.o_clipbord_success_alert').show();
                });
            });
            new ZeroClipboard(self.$('.o_clipbord_success_alert'));
        });
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
            'width=626,height=436');
    }
});


var DashboardShare = DashboardGift.extend({
    template: 'DashboardShare',
    init: function(parent, data){
        this.data = data;
        this.parent = parent;
        this.share_url = 'http://www.odoo.com/';
        this.share_text = encodeURIComponent("#IamUsingOdoo, an Open-Source Web App that manages my Sales, Projects, Accounting, Website, Warehouse, Shop and more");
    }
});

core.action_registry.add('web_dashboard.main', Dashboard);

return {
    Dashboard: Dashboard,
    DashboardInvitations: DashboardInvitations,
    DashboardPlanner: DashboardPlanner,
    DashboardGift: DashboardGift,
};

});