openerp.gdocs = function(instance) {

instance.web.form.SidebarAttachments = instance.web.form.SidebarAttachments.extend({
    on_attachments_loaded: function(attachments) {
        alert('gdocs.js.on_attachments_loaded()');
        this._super(attachments);
        var self = this;
        var $gdocbtn = self.$element.find('button.gdocs');
        var is_gdoc = function(a) {
            return a.type == 'url' && a.name == 'GDocs';
        };
        if (_.any(attachments, is_gdoc)) {
            $gdocbtn.hide();
        } else {
            $gdocbtn.show().click(self.on_add_gdoc);
        }
    },
    on_add_gdoc: function() {
        var self = this;
        var $gdocbtn = this.$element.find('button.gdocs');alert($gdocbtn);
        $gdocbtn.attr('disabled', 'true').find('img, span').toggle();
        this.view.dataset.call_button('copy_gdoc', [[this.view.datarecord.id], this.view.dataset.get_context()], function(r) {
            $gdocbtn.hide();
            self.do_update();
            self.do_action(r.result);
        });
    }
});

};
