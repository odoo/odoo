openerp.google_docs = function(instance, session) {


        instance.web.form.SidebarAttachments = instance.web.form.SidebarAttachments.extend({
            init: function() {
                this._super.apply(this, arguments);
                this.$element.delegate('.oe_google_docs_text_button', 'click', this.on_add_text_gdoc);
            },


           on_attachments_loaded: function(attachments) {
               this._super(attachments);
               var config = new instance.web.DataSet(this, 'google.docs.config', this.view.dataset.get_context());
               config.call('get_config', [[this.view.datarecord.id],this.view.dataset.model,this.view.dataset.get_context()], function(r) {
               if (r == false){
                    $('.oe_google_docs_text_button',this.$element).hide();
               }
               });
           },

            on_add_text_gdoc: function() {
                var self = this;
                var $gdocbtn = this.$element.find('.oe_google_docs_text_button');
                $gdocbtn.attr('disabled', 'true').find('img, span').toggle();
                var ds = new instance.web.DataSet(this, 'google.docs', this.view.dataset.get_context());
                ds.call('doc_get', [this.view.dataset.model, [this.view.datarecord.id], 'text'], function(r) {
                    if (r == 'False') {
                        var params = {
                            error: response,
                            message: "The user google credentials are not set yet. Contact your administrator for help."
                        }
                        $(openerp.web.qweb.render("DialogWarning", params)).dialog({
                            title: "User Google credentials are not yet set.",
                            modal: true,
                        });
                    }
                    self.do_update();
                });
            },
        });
};

