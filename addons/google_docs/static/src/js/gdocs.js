openerp.google_docs = function(instance, session) {


        instance.web.form.SidebarAttachments = instance.web.form.SidebarAttachments.extend({
            init: function() {
                this._super.apply(this, arguments);
                var self = this;
                var config = new instance.web.DataSet(this, 'google.docs.config', this.view.dataset.get_context());
                config.call('get_config', [this.view.dataset.ids[this.view.dataset.index]], function(r) {
                    console.log(r);
                    // if the configuration isn't set, the buttons should be hidden.
                    if (r==false) {
                        $('.oe_google_docs_text_button').css('display', 'none');

                        return;
                    }

                    var attachment = new instance.web.DataSet(this, 'ir.attachment', self.view.dataset.get_context());
                    attachment.call('copy_gdoc', [self.view.dataset.model, [self.view.datarecord.id]], function(res) {
                        console.log(res);
                    });
                });
            },
            on_add_gdoc: function() {
                var self = this;
                var $gdocbtn = this.$element.find('.oe_google_docs_text_button');
                $gdocbtn.attr('disabled', 'true').find('img, span').toggle();
                var ds = new instance.web.DataSet(this, 'google.docs', this.view.dataset.get_context());
                ds.call('doc_get', [this.view.dataset.model, [this.view.datarecord.id], 'text'], function(r) {
                    console.log(r);
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

