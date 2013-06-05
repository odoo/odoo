openerp.pad = function(instance) {
    
    instance.web.form.FieldPad = instance.web.form.AbstractField.extend(instance.web.form.ReinitializeWidgetMixin, {
        template: 'FieldPad',
        content: "",
        init: function() {
            this._super.apply(this, arguments);
            this.set("configured", true);
            this.on("change:configured", this, this.switch_configured);
        },
        initialize_content: function() {
            var self = this;
            this.switch_configured();
            this.$('.oe_pad_switch').click(function() {
                self.$el.toggleClass('oe_pad_fullscreen');
            });
            this.render_value();
        },
        switch_configured: function() {
            this.$(".oe_unconfigured").toggle(! this.get("configured"));
            this.$(".oe_configured").toggle(this.get("configured"));
        },
        render_value: function() {
            var self  = this;
            if (this.get("configured") && ! this.get("value")) {
                self.view.dataset.call('pad_generate_url', {
                    context: {
                        model: self.view.model,
                        field_name: self.name,
                        object_id: self.view.datarecord.id
                    },
                }).done(function(data) {
                    if (! data.url) {
                        self.set("configured", false);
                    } else {
                        self.set("value", data.url);
                    }
                });
            }
            this.$('.oe_pad_content').html("");
            var value = this.get('value');
            if (this.pad_loading_request) {
                this.pad_loading_request.abort();
            }
            if (_.str.startsWith(value, 'http')) {
                if (! this.get('effective_readonly')) {
                    var content = '<iframe width="100%" height="100%" frameborder="0" src="' + value + '?showChat=false&userName=' + this.session.username + '"></iframe>';
                    this.$('.oe_pad_content').html(content);
                    this._dirty_flag = true;
                } else {
                    this.content = '<div class="oe_pad_loading">... Loading pad ...</div>';
                    this.pad_loading_request = $.get(value + '/export/html').done(function(data) {
                        groups = /\<\s*body\s*\>(.*?)\<\s*\/body\s*\>/.exec(data);
                        data = (groups || []).length >= 2 ? groups[1] : '';
                        self.$('.oe_pad_content').html('<div class="oe_pad_readonly"><div>');
                        self.$('.oe_pad_readonly').html(data);
                    }).fail(function() {
                        self.$('.oe_pad_content').text('Unable to load pad');
                    });
                }
            }
        },
    });

    instance.web.form.widgets = instance.web.form.widgets.extend({
        'pad': 'instance.web.form.FieldPad',
    });
};
