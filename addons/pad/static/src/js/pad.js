openerp.pad = function(instance) {
    
    instance.web.form.FieldPad = instance.web.form.AbstractField.extend({
        template: 'FieldPad',
        configured: false,
        content: "",
        set_value: function(val) {
            var self = this;
            var _super = self._super;
            _super.apply(self,[val]);

            if (val === false || val === "") {
                self.field_manager.dataset.call('pad_generate_url',{context:{
                        model: self.field_manager.model,
                        field_name: self.name,
                        object_id: self.field_manager.datarecord.id
                    }}).then(function(data) {
                    if(data&&data.url){
                        _super.apply(self,[data.url]);
                        self.renderElement();
                    }
                });
            } else {
                self.renderElement();
            }
            this._dirty_flag = true;
        },
        renderElement: function(){
            var self  = this;
            var value = this.get('value');
            if(!_.str.startsWith(value,'http')){
                this.configured = false;
                this.content = "";
            }else{
                this.configured = true;
                if(!this.get('effective_readonly')){
                    this.content = '<iframe width="100%" height="100%" frameborder="0" src="'+value+'?showChat=false&userName='+this.session.username+'"></iframe>';
                }else{
                    this.content = '<div class="oe_pad_loading">... Loading pad ...</div>';
                    $.get(value+'/export/html').success(function(data){
                        self.$('.oe_pad_content').html('<div class="oe_pad_readonly">'+data+'<div>');
                    }).error(function(){
                        self.$('.oe_pad_content').text('Unable to load pad');
                    });
                }
            }
            this._super();
            this.$('.oe_pad_content').html(this.content);
            this.$('.oe_pad_switch').click(function(){
                self.$el.toggleClass('oe_pad_fullscreen');
            });
            this.on('change:effective_readonly',this,function(){
                self.renderElement();
            });
        },
    });

    instance.web.form.widgets = instance.web.form.widgets.extend({
        'pad': 'instance.web.form.FieldPad',
    });
};
