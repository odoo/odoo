
openerp.share = function(session) {

    var has_action_id = false;

    function launch_wizard(self, view, user_type, invite) {
        var action = view.getParent().action;
        var Share = new session.web.DataSet(self, 'share.wizard', view.dataset.get_context());
        var domain = new session.web.CompoundDomain(view.dataset.domain);
        if (view.fields_view.type == 'form') {
            domain = new session.web.CompoundDomain(domain, [['id', '=', view.datarecord.id]]);
        }
        if (view.fields_view.type == 'form') rec_name = view.datarecord.name;
        else rec_name = '';
        self.rpc('/web/session/eval_domain_and_context', {
            domains: [domain],
            contexts: [view.dataset.context]
        }, function (result) {
            Share.create({
                name: action.name,
                record_name: rec_name,
                domain: result.domain,
                action_id: action.id,
                user_type: user_type || 'embedded',
                view_type: view.fields_view.type,
                invite: invite || false,
            }, function(result) {
                var share_id = result.result;
                var step1 = Share.call('go_step_1', [[share_id],], function(result) {
                    var action = result;
                    self.do_action(action);
                });
            });
        });
    }

    function has_share(yes, no) {
        if (!session.session.share_flag) {
            session.session.share_flag = $.Deferred(function() {
                var func = new session.web.Model("share.wizard").get_func("has_share");
                func(session.session.uid).pipe(function(res) {
                    if(res) {
                        session.session.share_flag.resolve();
                    } else {
                        session.session.share_flag.reject();
                    }
                });
            });
        }
        session.session.share_flag.done(yes).fail(no);
    }

    /* Extend the Sidebar to add Share and Embed links in the 'More' menu */
    session.web.Sidebar = session.web.Sidebar.extend({

        start: function() {
            var self = this;
            this._super(this);
            has_share(function() {
                self.add_items('other', [
                    {   label: 'Share',
                        callback: self.on_click_share,
                        classname: 'oe_share' },
                    {   label: 'Embed',
                        callback: self.on_click_share_link,
                        classname: 'oe_share' },
                ]);
            });
        },

        on_click_share: function(item) {
            var view = this.getParent()
            launch_wizard(this, view, 'emails', false);
        },

        on_click_share_link: function(item) {
            var view = this.getParent()
            launch_wizard(this, view, 'embedded', false);
        },
    });

    /**
     * Extends mail (Chatter widget)
     * - show the 'invite' button' only we came on the form view through
     *   an action. We do this because 'invite' is based on the share
     *   mechanism, and it tries to share an action.
     */
    session.mail.RecordThread.include( {
        start: function() {
            start_res = this._super.apply(this, arguments);
            if (has_action_id) {
                this.$element.find('button.oe_share_invite').show();
            }
            return start_res;
        }
    });

    session.web.ViewManagerAction.include({
        start: function() {
            var self = this;
            this.check_if_action_is_defined();
            has_share(function() {
                self.$element.delegate('button.oe_share_invite', 'click', self.on_click_share_invite);
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
};

