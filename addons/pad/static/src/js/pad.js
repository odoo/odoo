openerp.pad = function(instance) {

var QWeb = instance.web.qweb;
QWeb.add_template('/pad/static/src/xml/pad.xml');

instance.web.form.SidebarAttachments = instance.web.form.SidebarAttachments.extend({
    on_attachments_loaded: function(attachments) {
        this._super(attachments);
        var self = this;
        var $padbtn = self.$element.find('button.pad');
        var is_pad = function(a) {
            return a.type == 'url' && _(a.url).startsWith(self.pad_prefix);
        };
        if (_.any(attachments, is_pad)) {
            $padbtn.hide();
        } else {
            $padbtn.show().click(self.on_add_pad);
        }
    },
    on_add_pad: function() {
        var self = this;
        var $padbtn = this.$element.find('button.pad');
        $padbtn.attr('disabled', 'true').find('img, span').toggle();
        this.view.dataset.call_button('pad_get', [[this.view.datarecord.id], this.view.dataset.get_context()], function(r) {
            $padbtn.hide();
            self.do_update();
            self.do_action(r.result);
        });
    }
});

};
