odoo.define('web_settings_dashboard', function (require) {
"use strict";

var AbstractAction = require('web.AbstractAction');
var core = require('web.core');
var framework = require('web.framework');
var Widget = require('web.Widget');

var QWeb = core.qweb;
var _t = core._t;

var Dashboard = AbstractAction.extend({
    template: 'DashboardMain',

    init: function(){
        this.all_dashboards = ['apps', 'invitations', 'share', 'translations', 'company'];
        return this._super.apply(this, arguments);
    },

    start: function(){
        return this.load(this.all_dashboards);
    },

    load: function(dashboards){
        var self = this;
        var loading_done = new $.Deferred();
        this._rpc({route: '/web_settings_dashboard/data'})
            .then(function (data) {
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

    load_translations: function (data) {
        return new DashboardTranslations(this, data.translations).replace(this.$('.o_web_settings_dashboard_translations'));
    },

    load_company: function (data) {
        return new DashboardCompany(this, data.company).replace(this.$('.o_web_settings_dashboard_company'));
    }
});

var DashboardInvitations = Widget.extend({
    template: 'DashboardInvitations',
    events: {
        'click .o_web_settings_dashboard_invite': '_onClickInvite',
        'click .o_web_settings_dashboard_access_rights': 'on_access_rights_clicked',
        'click .o_web_settings_dashboard_user': 'on_user_clicked',
        'click .o_web_settings_dashboard_more': 'on_more',
        'click .o_badge_remove': '_onClickBadgeRemove',
        'keydown textarea#user_emails': '_onKeydownUserEmails',
    },
    init: function(parent, data){
        this.data = data;
        this.parent = parent;
        this.emails = [];
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Create badges for valid and unique emails
     *
     * @private
     */
    _createBadges: function () {
        var $userEmails = this.$('#user_emails');
        var value = $userEmails.val().trim();
        if (value) {
            var emails = _.uniq(value.split(/[ ,\n]+/));
            if (this._validateEmails(emails)) {
                // Check emails already exist in invite and pending
                var pendingEmails = _.map(this.data.pending_users, function (email) { return email[1]; });
                if (_.difference(emails, this.emails.concat(pendingEmails)).length == emails.length) {
                    this.emails = this.emails.concat(emails);
                    $userEmails.before(QWeb.render('EmailBadge', {'emails': emails}));
                    $userEmails.val('');
                } else {
                    this.do_warn(_t('Email address already exist'), '');
                }
            } else {
                this.do_warn(_t('Please provide valid email address'), '');
            }
        }
    },
    /**
     * Remove badge
     *
     * @private
     * @param {jQueryElement} $badge
     */
    _removeBadge: function ($badge) {
        var email = $badge.text().trim();
        this.emails = _.without(this.emails, email);
        $badge.remove();
    },
    /**
     * @private
     * @param {string[]} emails
     * @returns {boolean} emails are valid or not
     */
    _validateEmails: function (emails) {
        var re = /^([\w-]+(?:\.[\w-]+)*)@((?:[\w-]+\.)*\w[\w-]{0,66})\.([a-z]{2,63}(?:\.[a-z]{2})?)$/i;
        return _.every(emails, function (email) {
            return re.test(email);
        });
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
            name: _t('Users'),
            type: 'ir.actions.act_window',
            view_type: 'form',
            view_mode: 'tree,form',
            res_model: 'res.users',
            domain: [['log_ids', '=', false]],
            context: {'search_default_no_share': true},
            views: [[false, 'list'], [false, 'form']],
        };
        this.do_action(action,{
            on_reverse_breadcrumb: function(){ return self.reload();}
        });
    },
    reload:function(){
        return this.parent.load(['invitations']);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} event
     */
    _onClickBadgeRemove: function (event) {
        var $badge = this.$(event.target).closest('.badge');
        this._removeBadge($badge);
    },
    /**
     * @private
     * @param {MouseEvent} event
     */
    _onClickInvite: function (event) {
        var self = this;
        this._createBadges();
        if (this.emails.length) {
            var $button = this.$(event.target);
            $button.button('loading');
            this._rpc({
                model: 'res.users',
                method: 'web_dashboard_create_users',
                args: [this.emails],
            })
            .then(function () {
                self.reload();
            })
            .fail(function () {
                $button.button('reset');
            });
        }
    },
    /**
     * @private
     * @param {KeyboardEvent} event
     */
     _onKeydownUserEmails: function (event) {
        var $userEmails = this.$(event.target);
        var keyCodes = [$.ui.keyCode.TAB, $.ui.keyCode.COMMA, $.ui.keyCode.ENTER, $.ui.keyCode.SPACE];
        if (_.contains(keyCodes, event.keyCode)) {
            event.preventDefault();
            this._createBadges();
        }
        // Remove Emails on backspace
        if (event.keyCode === $.ui.keyCode.BACKSPACE && this.emails.length && !$userEmails.val()) {
            this._removeBadge($userEmails.prev('.badge'));
        }
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

    init: function (parent, data) {
        this.data = data;
        this.parent = parent;
        this.share_url = 'https://www.odoo.com';
        this.share_text = encodeURIComponent("I am using #Odoo - Awesome open source business apps.");
    },

    /**
     * @param {MouseEvent} ev
     */
    share_twitter: function (ev) {
        ev.preventDefault();
        var popup_url = _.str.sprintf( 'https://twitter.com/intent/tweet?tw_p=tweetbutton&text=%s %s',this.share_text,this.share_url);
        this.sharer(popup_url);
    },
    /**
     * @param {MouseEvent} ev
     */
    share_facebook: function (ev) {
        ev.preventDefault();
        var popup_url = _.str.sprintf('https://www.facebook.com/sharer/sharer.php?u=%s', encodeURIComponent(this.share_url));
        this.sharer(popup_url);
    },

    /**
     * @param {MouseEvent} ev
     */
    share_linkedin: function (ev) {
        ev.preventDefault();
        var popup_url = _.str.sprintf('http://www.linkedin.com/shareArticle?mini=true&url=%s&title=I am using odoo&summary=%s&source=www.odoo.com', encodeURIComponent(this.share_url), this.share_text);
        this.sharer(popup_url);
    },

    sharer: function (popup_url) {
        window.open(
            popup_url,
            'Share Dialog',
            'width=600,height=400'); // We have to add a size otherwise the window pops in a new tab
    }
});

var DashboardTranslations = Widget.extend({
    template: 'DashboardTranslations',

    events: {
        'click .o_load_translations': 'on_load_translations'
    },

    on_load_translations: function () {
        this.do_action('base.action_view_base_language_install');
    }

});

var DashboardCompany = Widget.extend({
    template: 'DashboardCompany',

    events: {
        'click .o_setup_company': 'on_setup_company'
    },

    init: function (parent, data) {
        this.data = data;
        this.parent = parent;
        this._super.apply(this, arguments);
    },

    on_setup_company: function () {
        var self = this;
        var action = {
            type: 'ir.actions.act_window',
            res_model: 'res.company',
            view_mode: 'form',
            view_type: 'form',
            views: [[false, 'form']],
            res_id: this.data.company_id
        };
        this.do_action(action, {
            on_reverse_breadcrumb: function () { return self.reload(); }
        });
    },

    reload: function () {
        return this.parent.load(['company']);
    }
});

core.action_registry.add('web_settings_dashboard.main', Dashboard);

return {
    Dashboard: Dashboard,
    DashboardApps: DashboardApps,
    DashboardInvitations: DashboardInvitations,
    DashboardShare: DashboardShare,
    DashboardTranslations: DashboardTranslations,
    DashboardCompany: DashboardCompany
};

});
