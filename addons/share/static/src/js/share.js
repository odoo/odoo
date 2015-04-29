odoo.define('share.share', function (require) {

var mail = require('mail.mail');
var core = require('web.core');
var data = require('web.data');
var Model = require('web.Model');
var pyeval = require('web.pyeval');
var session = require('web.session');
var Sidebar = require('web.Sidebar');
var ViewManager = require('web.ViewManager');

var _t = core._t;
var has_action_id = false;

function launch_wizard(self, view, user_type, invite) {
    var action = view.getParent().action;
    var Share = new data.DataSet(self, 'share.wizard', view.dataset.get_context());
    var domain = new data.CompoundDomain(view.dataset.domain);
    var rec_name;
    if (view.fields_view.type == 'form') {
        domain = new data.CompoundDomain(domain, [['id', '=', view.datarecord.id]]);
    }
    if (view.fields_view.type == 'form') rec_name = view.datarecord.name;
    else rec_name = '';
    pyeval.eval_domains_and_contexts({
        domains: [domain],
        contexts: [Share.get_context()]
    }).done(function (result) {
        Share.create({
            name: action.name,
            record_name: rec_name,
            domain: result.domain,
            action_id: action.id,
            user_type: user_type || 'embedded',
            view_type: view.fields_view.type,
            invite: invite || false,
        }).done(function(share_id) {
            Share.call('go_step_1', [[share_id], Share.get_context()]).done(function(result) {
                var action = result;
                self.do_action(action);
            });
        });
    });
}

function has_share(yes, no) {
    if (!session.share_flag) {
        session.share_flag = $.Deferred(function() {
            var func = new Model("share.wizard").get_func("has_share");
            func(session.uid).then(function(res) {
                if(res) {
                    session.share_flag.resolve();
                } else {
                    session.share_flag.reject();
                }
            });
        });
    }
    session.share_flag.done(yes).fail(no);
}

/* Extend the Sidebar to add Share and Embed links in the 'More' menu */
Sidebar.include({
    init: function(parent) {
        var self = this;
        this._super(parent);
        has_share(function() {
            self.add_items('other', [
                {   label: _t('Share'),
                    callback: self.on_click_share,
                    classname: 'oe_share' },
                {   label: _t('Embed'),
                    callback: self.on_click_share_link,
                    classname: 'oe_share' },
            ]);
        });
    },

    on_click_share: function() {
        var view = this.getParent();
        launch_wizard(this, view, 'emails', false);
    },

    on_click_share_link: function() {
        var view = this.getParent();
        launch_wizard(this, view, 'embedded', false);
    },
});

/**
 * Extends mail (Chatter widget)
 * - show the 'invite' button' only we came on the form view through
 *   an action. We do this because 'invite' is based on the share
 *   mechanism, and it tries to share an action.
 */
mail.TimelineRecordThread.include( {
    start: function() {
        var start_res = this._super.apply(this, arguments);
        if (has_action_id) {
            this.$el.find('button.oe_share_invite').show();
        }
        return start_res;
    }
});

ViewManager.include({
    start: function() {
        var self = this;
        this.check_if_action_is_defined();
        has_share(function() {
            self.$el.delegate('button.oe_share_invite', 'click', self.on_click_share_invite);
        });
        return this._super.apply(this, arguments);
    },

    check_if_action_is_defined: function() {
        if (this.action && this.action.id) {
            has_action_id = true;
        }
        else {
            has_action_id = false;
        }
    },

    on_click_share_invite: function(e) {
        e.preventDefault();
        launch_wizard(this, this.views[this.active_view].controller, 'emails', true);
    },
});

});
