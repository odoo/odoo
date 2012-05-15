openerp.pad = function(instance) {

instance.web.form.FieldEtherpad = instance.web.form.AbstractField.extend(_.extend({}, instance.web.form.ReinitializeFieldMixin, {
    template: 'FieldEtherpad',
    initialize_content: function() {
        this.$textarea = undefined;         
        this.$element.find('span').text(this.field.string);
        this.$element.find('span').click(_.bind(function(ev){
            this.$element.find('span').toggleClass('etherpad_zoom_head');
            var iszoom = this.$element.find('span').hasClass('etherpad_zoom_head');
            this.$element.find('span').text((iszoom?'Back to Task':this.field.string));
            this.$element.find('div').toggleClass('etherpad_zoom');
            $("body").toggleClass('etherpad_body');            
            },this));            
        },
        set_value: function(value_) {
            this._super(value_);
            this.render_value();
        },
        render_value: function() {            
            var show_value = instance.web.format_value(this.get('value'), this, '');                        
            if (!this.get("effective_readonly")) {
                console.log("this is sthis...",this); 
                var pad_username = "noNamed" ;
                if(this.view.datarecord.hasOwnProperty("pad_username"))
                    pad_username = this.view.datarecord.pad_username;
                this.$element.find('div').html('<iframe width="100%" height="100%" frameborder="0"  src="'+show_value.split('\n')[0]+'?showChat=false&showLineNumbers=false&userName='+pad_username+'"></iframe>');
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
