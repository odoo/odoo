openerp.web_etherpad = function (instance) {
    
    instance.web.form.FieldEtherpad = instance.web.form.AbstractField.extend(_.extend({}, instance.web.form.ReinitializeFieldMixin, {
        template: 'FieldEtherpad',
        initialize_content: function() {
            this.$textarea = undefined;
            if (!this.get("effective_readonly")) {
                this.$textarea = this.$element.find('textarea');
                //this.$textarea.hide();
                this.$textarea.change(_.bind(function() {
                    this.set({'value': instance.web.parse_value(this.$textarea.val(), this)});
                }, this));
                this.resized = false;
            }
        },
        set_value: function(value_) {
            var self = this ;
            var company_id = (self.view.datarecord.hasOwnProperty('id')) ?self.view.datarecord.company_id[0]: self.view.datarecord.company_id ;
              /* getting etherpad url and set pad to field. */
              self.rpc('/web/dataset/get',{
                   'model':'res.company',
                   'ids':[company_id],
                   'fields':['pad_url_template'],
                   'context':{}
                },function(companies){
                     var pad_template = companies[0].pad_url_template.replace('-%(salt)s-%(name)s','').replace(/\s/g,'');                      
 
                       var patt_url = (_.str.sprintf(pad_template.replace('-%(id)d',''), {
                                              db : self.session.db, 
                                              model : self.view.model,                                                    
                                           })).replace(/\s/g,'') ;                      
                       //alert("match or not >?"+value_.search(patt_url));                       
                       if(value_ == false)
                            self.add_pad(self,pad_template,value_);
                       else if(value_.search(patt_url) != 0)
                            self.add_pad(self,pad_template,value_);
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
            self.update_dom();
            self.render_value();
        },
        add_pad: function(self,pad_template,value_){  
            var url = (_.str.sprintf(pad_template, {
                  db : self.session.db, 
                  model : self.view.model,          
                  id : Math.round(new Date().getTime()/100.0),
                                 })).replace(/\s/g,''); 
            var show_value = instance.web.format_value(value_, this, '');
            self.show_pad_value(self,url + '\n'+ show_value);
            this.dirty = true;
        },        
        render_value: function() {            
            var show_value = instance.web.format_value(this.get('value'), this, '');            
            if (!this.get("effective_readonly")) {            
                this.$textarea.val(show_value);                
                this.$element.find('div').html('<iframe frameborder="0" height="217px" width="100%" src="'+show_value.split('\n')[0]+'?showChat=false"></iframe>'); 
                if (!this.resized && this.view.options.resize_textareas) {
                    this.do_resize(this.view.options.resize_textareas);
                    this.resized = true;
                }
            } else {    
                this.$element.text(show_value);
                if(this.get('value') != false)
                {
                    var self = this;             
                    $.get(show_value.split('\n')[0]+'/export/html', function(data) {                                      
                    console.log(data);                    
                        self.$element.html(data);
                    });
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


}
