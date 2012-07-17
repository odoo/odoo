openerp.pad = function(instance) {

instance.web.form.FieldEtherpad = instance.web.form.AbstractField.extend(_.extend({}, instance.web.form.ReinitializeFieldMixin, {
    template: 'FieldEtherpad',
    initialize_content: function() {
        this.$textarea = undefined;         
        this.$element.find('div.oe_etherpad_head').click(_.bind(function(ev){
            this.$element.toggleClass('oe_etherpad_fullscreen').toggleClass('oe_etherpad_normal');

            },this));            
        },
        set_value: function(value_) {
            this._super(value_);
            this.render_value();
        },
        render_value: function() {            
            var show_value = instance.web.format_value(this.get('value'), this, '');                        
            if (!this.get("effective_readonly")) {                
                var pad_username = this.session.username;
                this.$element.find('div.oe_etherpad_default').html('<iframe width="100%" height="100%" frameborder="0"  src="'+show_value.split('\n')[0]+'?showChat=false&showLineNumbers=false&userName='+pad_username+'"></iframe>');
            } else {
                if(this.get('value') != false)
                {
                    var self = this;
                    if(show_value.split('\n')[0] != '')             
                        $.get(show_value.split('\n')[0]+'/export/html')
                        .success(function(data) { self.$element.html('<div class="etherpad_readonly">'+data+'</div>'); })
                        .error(function() { self.$element.text('Unable to load pad'); });
                }                    
            }
        },                
    }));    
    
    instance.web.form.widgets = instance.web.form.widgets.extend({
        'etherpad': 'instance.web.form.FieldEtherpad',
    });
};  
