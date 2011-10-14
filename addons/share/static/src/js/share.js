
openerp.share = function(instance) {

instance.web.Sidebar = instance.web.Sidebar.extend({

    add_default_sections: function() {
        this._super();
        this.add_items('other', [{
            label: 'Share',
            callback: this.on_sidebar_click_share,
            classname: 'oe_share',
        }]);
    },

    on_sidebar_click_share: function(item) {
        var self = this;
        var view = this.widget_parent
        var action = view.widget_parent.action;

        var Share = new instance.web.DataSet(this, 'share.wizard', view.dataset.get_context());

        Share.create({
            name: action.name,
            domain: view.dataset.domain,
            action_id: action.id,
        }, function(result) {
            var share_id = result.result;
            console.log('share_id', share_id);

            var step1 = Share.call('go_step_1', [[share_id],], function(result) {
                var action = result;
                console.log('step1', action);
                self.do_action(action);
            });
        });

    },

});

};
