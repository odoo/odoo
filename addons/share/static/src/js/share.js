
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
        if (!session.connection.share_flag) {
            session.connection.share_flag = $.Deferred(function() {
                var func = new session.web.Model("share.wizard").get_func("has_share");
                func(session.connection.uid).pipe(function(res) {
                    if(res) {
                        session.connection.share_flag.resolve();
                    } else {
                        session.connection.share_flag.reject();
                    }
                });
            });
        }
        session.connection.share_flag.done(yes).fail(no);
    }

    session.web.Sidebar = session.web.Sidebar.extend({
        add_default_sections: function() {
            this._super();
            var self = this;
            has_share(function() {
                self.add_items('other', [{
                    label: 'Share',
                    callback: self.on_sidebar_click_share,
                    classname: 'oe-share',
                }]);
            });
        },
        on_sidebar_click_share: function(item) {
            var view = this.getParent()
            launch_wizard(this, view);
        },
    });

    session.mail.RecordThread.include( {
        start: function() {
            start_res = this._super.apply(this, arguments);
            if (has_action_id) {
                this.$element.find('button.oe-share-mail').show();
            }
            return start_res;
        }
    });

    session.web.ViewManagerAction.include({
        start: function() {
            var self = this;
            this.check_if_action_is_defined();
            has_share(function() {
                self.$element.find('a.oe-share_link').click(self.on_click_share_link);
                self.$element.find('a.oe-share').click(self.on_click_share);
                self.$element.delegate('button.oe-share-mail', 'click', self.on_click_share_mail);
            }, function() {
                self.$element.find('a.oe-share_link').remove();
                self.$element.find('a.oe-share').remove();
            });
            return this._super.apply(this, arguments);
        },
    
        check_if_action_is_defined: function() {
            if (this.action && this.action.id) {
                has_action_id = true;
                this.$element.find('a.oe-share_link').show();
                this.$element.find('a.oe-share').show();            
            }
            else {
                has_action_id = false;
            }
        },
    
        on_click_share_link: function(e) {
            e.preventDefault();
            launch_wizard(this, this.views[this.active_view].controller, 'embedded', false);
        },
        on_click_share: function(e) {
            e.preventDefault();
            launch_wizard(this, this.views[this.active_view].controller, 'emails', false);
        },
        on_click_share_mail: function(e) {
            e.preventDefault();
            launch_wizard(this, this.views[this.active_view].controller, 'emails', true);
        },
    });
};

