
openerp.share = function(instance) {

function launch_wizard(self, view) {
        var action = view.widget_parent.action;
        var Share = new instance.web.DataSet(self, 'share.wizard', view.dataset.get_context());
        var domain = new instance.web.CompoundDomain(view.dataset.domain);
        if (view.fields_view.type == 'form') {
            domain = new instance.web.CompoundDomain(domain, [['id', '=', view.datarecord.id]]);
        }
        self.rpc('/web/session/eval_domain_and_context', {
            domains: [domain],
            contexts: [view.dataset.context]
        }, function (result) {
            Share.create({
                name: action.name,
                domain: result.domain,
                action_id: action.id,
                view_type: view.fields_view.type,
            }, function(result) {
                var share_id = result.result;
                var step1 = Share.call('go_step_1', [[share_id],], function(result) {
                    var action = result;
                    self.do_action(action);
                });
            });
        });
}

var _has_share = null;
function if_has_share(yes, no) {
    if (!_has_share) {
        _has_share = $.Deferred(function() {
            var self = this;
            instance.connection.on_session_invalid.add_last(function() { _has_share = null; });
            var func = new instance.web.Model(null, "share.wizard").get_func("has_share");
            func(instance.connection.uid).pipe(function(res) {
                if(res) {
                    self.resolve();
                } else {
                    self.reject();
                }
            });
        });
    }
    _has_share.done(yes).fail(no);
}


instance.web.Sidebar = instance.web.Sidebar.extend({
    add_default_sections: function() {
        this._super();
        var self = this;
        if_has_share(function() {
            self.add_items('other', [{
                label: 'Share',
                callback: self.on_sidebar_click_share,
                classname: 'oe-share',
            }]);
        });
    },
    on_sidebar_click_share: function(item) {
        var view = this.widget_parent
        launch_wizard(this, view);
    },
});

instance.web.ViewManagerAction.include({
    start: function() {
        var self = this;
        if_has_share(function() {
            self.$element.find('a.oe-share').click(self.on_click_share);
        }, function() {
            self.$element.find('a.oe-share').remove();
        });
        return this._super.apply(this, arguments);
    },
    on_click_share: function(e) {
        e.preventDefault();
        launch_wizard(this, this.views[this.active_view].controller);
    },
});

};
