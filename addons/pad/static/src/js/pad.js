openerp.pad = function(instance) {

instance.web.Sidebar = instance.web.Sidebar.extend({
    init: function(parent) {
        this._super(parent);
        this.add_items('other',[{ label: "Pad", callback: this.on_add_pad }]);
    },
    on_add_pad: function() {
        var self = this;
        var view = this.getParent();
        var model = new instance.web.Model('ir.attachment');
        model.call('pad_get', [view.model ,view.datarecord.id],{}).then(function(r) {
            self.do_action({ type: "ir.actions.act_url", url: r });
        });
    }
});

};
