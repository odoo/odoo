openerp.pad = function(instance) {

instance.web.form.FieldPad = instance.web.form.AbstractField.extend({
    template: 'FieldPad',
    start: function() {
        this._super();
        var self = this;
        this.$el.find('div.oe_pad_head').click(function(ev) {
            self.$el.toggleClass('oe_pad_fullscreen');
        });
        this.on("change:effective_readonly", this, function() {
            this.render_value();
        });
    },
    set_value: function(val) {
        var self = this;
        var _super = self._super;
        _super.apply(self,[val]);
        this._dirty_flag = true;
        self.render_value();
    },
    render_value: function() {
        console.log("display");
        var self = this;
        var value = this.get('value');

        if (!_.str.startsWith(value, "http")) {
            self.$('.oe_pad_content').html(instance.web.qweb.render('FieldPad.unconfigured'));
        } else {
            if (!this.get("effective_readonly")) {
                var pad_username = this.session.username;
                var code = '<iframe width="100%" height="100%" frameborder="0" src="'+value+'?showChat=false&userName='+pad_username+'"></iframe>';
                this.$('.oe_pad_content').html(code);
            } else {
                $.get(value+'/export/html').success(function(data) {
                    self.$('.oe_pad_content').html('<div class="oe_pad_readonly">'+data+'</div>');
                }).error(function() {
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
