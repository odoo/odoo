openerp.pad = function(instance) {

instance.web.Sidebar = instance.web.Sidebar.extend({
    init: function(parent) {
        this._super(parent);
        this.add_items('other',[{ label: "Pad", callback: this.on_add_pad }]);
    },
    on_add_pad: function() {
        var self = this;
        var view = this.getParent();
        var model = new instance.web.Model('ir.attachment');
        model.call('pad_get', [view.model ,view.datarecord.id],{}).then(function(r) {
            self.do_action({ type: "ir.actions.act_url", url: r });
        });
    }
});

instance.web.form.FieldEtherpad = instance.web.form.AbstractField.extend(_.extend({}, instance.web.form.ReinitializeFieldMixin, {
    template: 'FieldEtherpad',
    initialize_content: function() {
        this.$textarea = undefined;            
        this.$element.find('span').text(this.name);
        this.$element.find('span').click(_.bind(function(ev){
        this.$element.find('span').toggleClass('etherpad_zoom_head');
        this.$element.find('div').toggleClass('etherpad_zoom');
                $("body").toggleClass('etherpad_body');
            },this));
            if (!this.get("effective_readonly")) {
                this.$textarea = this.$element.find('textarea');
                this.$textarea.hide();
                this.$textarea.change(_.bind(function() {
                    this.set({'value': instance.web.parse_value(this.$textarea.val(), this)});
                }, this));
                this.resized = false;
            }
        },
        set_value: function(value_) {
            var self = this ;
            var show_value = instance.web.format_value(value_, this, '');
            var company_id = (self.view.datarecord.hasOwnProperty('id')) ?self.view.datarecord.company_id[0]: self.view.datarecord.company_id ;
              new instance.web.DataSet(this, 'res.company', {}).read_ids([company_id],['pad_url_template'],{}).then(function(res){              
              var pad_template = res[0].pad_url_template.replace('-%(salt)s-%(name)s','').replace(/\s/g,'');                      
 
              var patt_url = (_.str.sprintf(pad_template.replace('-%(id)d',''), {
                                              db : self.session.db, 
                                              model : self.view.model,                                                    
                                           })).replace(/\s/g,'') ;

               
              if(!self.view.datarecord.hasOwnProperty('id'))
                  self.add_pad(self,pad_template);
              else if(self.view.datarecord.hasOwnProperty('id') && show_value.search(patt_url) != 0){
                  self.add_pad(self,pad_template);
                  self.view.do_save();
              }
              else
                self.show_pad_value(self,value_);                
              });
        },
        show_pad_value: function(self,value_)
        {
            self._inhibit_on_change = true;
            self.set({'value': value_ });
            self._inhibit_on_change = false;
            self.invalid = false;
            self.render_value();
        },
        add_pad: function(self,pad_template){
            var url = (_.str.sprintf(pad_template, {
                  db : self.session.db, 
                  model : self.view.model,          
                  id : Math.round(new Date().getTime()/100.0),
                                 })).replace(/\s/g,''); 
            self.show_pad_value(self,url + '\n');
            self._dirty_flag = true ;                       
        },        
        render_value: function() {            
            var show_value = instance.web.format_value(this.get('value'), this, '');            
            if (!this.get("effective_readonly")) {            
                this.$textarea.val(show_value);
                this.$element.find('div').html('<iframe frameborder="0" height="100%" width="100%" src="'+show_value.split('\n')[0]+'?showChat=false"></iframe>');                 
                if (!this.resized && this.view.options.resize_textareas) {
                    this.do_resize(this.view.options.resize_textareas);
                    this.resized = true;
                }
            } else {    
                this.$element.text(show_value);
                if(this.get('value') != false)
                {
                    var self = this;
                    if(show_value.split('\n')[0] != '')             
                        $.get(show_value.split('\n')[0]+'/export/html')
                        .success(function(data) { self.$element.html(data); })
                        .error(function() { self.$element.text('Unable to load pad'); });
                    else
                        self.$element.text(show_value);
                }                    
            }
        },
        validate: function() {
            this.invalid = false;
            if (!this.get("effective_readonly")) {
                try {
                    var value_ = instance.web.parse_value(this.$textarea.val(), this, '');
                    this.invalid = this.get("required") && value_ === '';
                } catch(e) {
                    this.invalid = true;
                }
            }
        },
        focus: function($element) {
            this._super($element || this.$textarea);
        },
        do_resize: function(max_height) {
            max_height = parseInt(max_height, 10);
            var $input = this.$textarea,
                $div = $('<div style="position: absolute; z-index: 1000; top: 0"/>').width($input.width()),
                new_height;
            $div.text($input.val());
            _.each('font-family,font-size,white-space'.split(','), function(style) {
                $div.css(style, $input.css(style));
            });
            $div.appendTo($('body'));
            new_height = $div.height();
            if (new_height < 90) {
                new_height = 90;
            }
            if (!isNaN(max_height) && new_height > max_height) {
                new_height = max_height;
            }
            $div.remove();
            $input.height(new_height);
        },
        reset: function() {
            this.resized = false;
        }
    }));    
    
    instance.web.form.widgets = instance.web.form.widgets.extend({
        'etherpad': 'instance.web.form.FieldEtherpad',
    });
};  
