openerp.pad = function(instance) {

instance.web.form.FieldPad = instance.web.form.AbstractField.extend(instance.web.form.ReinitializeFieldMixin, {
    template: 'FieldPad',
    initialize_content: function() {
        var self = this;
        this.$textarea = undefined;
        this.$element.find('div.oe_etherpad_head').click(function(ev) {
            self.$element.toggleClass('oe_etherpad_fullscreen').toggleClass('oe_etherpad_normal');
        });
    },
    set_value: function(value_) {
        this._super(value_);
        this.render_value();
    },
    render_value: function() {
        var self = this;
        var value = this.get('value');
        if(value !== false) {
            var url = value.split('\n')[0];
            if (!this.get("effective_readonly")) {
                var pad_username = this.session.username;
                var code = '<iframe width="100%" height="100%" frameborder="0" src="'+url+'?showChat=false&userName='+pad_username+'"></iframe>';
                this.$element.find('div.oe_etherpad_default').html(code);
            } else {
                $.get(url+'/export/html').success(function(data) {
                    self.$element.html('<div class="etherpad_readonly">'+data+'</div>');
                }).error(function() {
                    self.$element.text('Unable to load pad');
                });
            }
        }
    },
});

instance.web.form.widgets = instance.web.form.widgets.extend({
    'pad': 'instance.web.form.FieldPad',
});

};
