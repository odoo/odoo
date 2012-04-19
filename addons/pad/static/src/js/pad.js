openerp.pad = function(instance) {

instance.web.Sidebar = instance.web.Sidebar.extend({
    init: function(parent) {
        this._super(parent);
        this.add_items('other',[{ label: "Pad", callback: this.on_add_pad }]);
    },
    on_attachments_loaded: function(attachments) {
        this._super(attachments);
        var self = this;
        var $padbtn = self.$element.find('button.pad');
        var is_pad = function(a) {
            return a.type == 'url' && a.name == 'Pad';
        };
    },
    on_add_pad: function() {
        var self = this;
        var view = this.getParent();
        view.dataset.call_button('pad_get', [[view.datarecord.id], view.dataset.get_context()], function(r) {
            self.do_update();
            self.do_action(r.result);
        });
    }
});

};
