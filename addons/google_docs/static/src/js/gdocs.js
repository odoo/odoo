console.log('fegegegwnw')
openerp.google_docs = function(instance) {

console.log('nw')
instance.web.form.SidebarAttachments = instance.web.form.SidebarAttachments.extend({
    init: function() {
        this._super.apply(this, arguments);
        this.$element.delegate('.oe_google_docs_button', 'click', self.on_add_gdoc);
    },
    on_add_gdoc: function() {
        var self = this;
console.log('--------');
        var $gdocbtn = this.$element.find('.oe_google_docs_button');
        $gdocbtn.attr('disabled', 'true').find('img, span').toggle();
        this.view.dataset.call_button('copy_gdoc', [[this.view.datarecord.id], this.view.dataset.get_context()], function(r) {
            $gdocbtn.hide();
            self.do_update();
            self.do_action(r.result);
        });
    }
});

};

