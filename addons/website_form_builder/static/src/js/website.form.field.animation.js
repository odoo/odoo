(function () {
    'use strict';

    var website = openerp.website;
    var _t = openerp._t;
    website.add_template_file('/website_form_builder/static/src/xml/website.form.editor.wizard.template.xml');

    /* 
        dict of selectors and associated functions to extract data from the form
    */

    var getDataForm = {
            'input[type=text]':     function($field) {return $field.attr('value') ? _.object([$field.attr('name')], [$field.attr('value')]) : null;},
            'input[type=hidden]':   function($field) {
                return getDataForm['input[type=text]'].call(this,$field);
            },
            'textarea':             function($field) {return getDataForm['input[type=text]'].call(this,$field);},
            'select':               function($field) {return getDataForm['input[type=text]'].call(this,$field);},
            ':has(input:checkbox)': function($field) {
                var n,args = [];
                $field.find('input').each(function (j,subelem) {
                    n = $(subelem).prop('name');
                    if($(subelem).is(':checked')) args.push($(subelem).val());
                });
                return (args.length) ? _.object([n],[args]):null;
                    
            },
            ':has(input:radio)': function($field) {
                var subelem = $field.find('input[type=radio]:checked');
                return subelem.val() ? _.object([$(subelem).prop('name')],[subelem.val()]): null;
            },
            ':has(textarea)': function($field) {
                var extracted_data = $.parseJSON($field.find('textarea').textext()[0].hiddenInput().val());
                var args = [];
                $.each(extracted_data, function (i, val) {
                    args.push(val.id);
                });
                return (args.length) ? _.object([$field.attr('name')],[args]) : null;
            },
            'input[type=file]': function($field) {
                var args = {};
                var size = $field.prop('files').length;
                $.each($field.prop('files'), function (i, val) {
                    args[$field.attr('name')+(($field.prop('files').length > 1)? '['+i+']':'')] = val;
                });
                return ($.isEmptyObject(args)) ? null:args;
                
            }
        };

    website.snippet.animationRegistry.form_builder_send = website.snippet.Animation.extend({
        selector: 'form[action*="/website_form/"]',
        start: function() {
            var self = this;
            this.$target.find('button').on('click',function(e) {self.send(e);});
        },
        stop: function() {
            this.$target.find('button').off('click');
        },
        indicateRequired: function(fail_required,empty_fields) {
            console.log('required', fail_required);
            console.log('empty', empty_fields);
            var i = 0, j=0;
            var field_required = null;
            var empty_field = null;
            var name = null;
            var len = (fail_required) ? fail_required.length:0;
            this.$target.find('.form-field').each(function(k,elem){

                name            = $(elem).find('.form-data').attr('name');
                field_required  = fail_required.indexOf(name);
                empty_field     = empty_fields.indexOf(name);
                fail_required   = _.without(fail_required,name);
                empty_fields    = _.without(empty_fields,name);
                $(elem)    .removeClass('has-error has-warning has-success has-feedback')
                           .find('i').remove();

                if(field_required >= 0){
                    $(elem) .addClass('has-error has-feedback').children('div')
                            .append('<i class="fa fa-close form-control-feedback"></i>');
                    i= i+1;
                }
                else if(empty_field >= 0){
                    $(elem) .addClass('has-warning has-feedback').children('div')
                            .append('<i class="fa fa-exclamation-triangle form-control-feedback"></i>');
                    j= j+1;
                }
                else $(elem).addClass('has-success has-feedback').children('div')
                            .append('<i class="fa fa-check form-control-feedback"></i>');
                                    
            });
        },
        send: function(e) {
                e.preventDefault();
                // if(!this.check()) return;
                var self              = this;
                var fail_required     = [];
                var empty_field       = [];
                var model             = this.$target.data('model');
                var args              = {"context": website.get_context()};

                var field_value;
                 this.field_label_list = {};
                var label;
                /*
                this.$target.find('.form-field').each(function(i,elem) {
                    label = $(elem).find('label').html();
                    if(label.length > 1) this.field_list[label] = $(elem).find('.form-data').attr('name'); 
                });
                */
                this.$target.find('.form-data').each(function(j,elem){
                    for (var i in getDataForm) {
                        if($(elem).is(i)) {
                            field_value = getDataForm[i].call(self, $(elem));
                            if(field_value) _.extend(args,field_value);
                            else if($(elem).attr('required')) fail_required.push($(elem).attr('name'));
                            else empty_field.push($(elem).attr('name'));

                            console.log(field_value);
                            console.log(empty_field);
                        }
                    }
                });
                if(fail_required.length) {
                    this.indicateRequired(fail_required,empty_field);
                    return;
                }
                
                var progress = $(openerp.qweb.render('website.form.editor.progress'))
                                    .appendTo('body')
                                    .modal({"keyboard" :true});

                var display_size = function(size) {
                
                    var order   = ['o', 'Ko', 'Mo', 'Go', 'To'];
                    var log1000 = Math.floor(Math.log(size)/Math.log(1000));
                    var integer = Math.floor(size/Math.pow(1000,log1000));
                    var decimal = Math.round((size - integer*Math.pow(1000,log1000))/(100*Math.pow(1000,log1000-1)));
                    var result  = integer+Math.round(decimal/10);
                    var order_l = order[Math.min(4,log1000)];
                    return result*Math.max(log1000-4, 1)+((result == integer) ? '.'+decimal:'')+order_l;

                };

                var success_page = this.$target.data('success');
                var fail_page = this.$target.data('fail');

                openerp.post('/website_form/'+model,args)
                .then(function(data) {
                        progress.modal('hide');
                        if(data) {
                            var len = (data.fail_required) ? data.fail_required.length:0;
                            if(data.id) $(location).attr('href',success_page);
                            else {
                                if(!len) $(location).attr('href',fail_page);
                                else self.indicateRequired(data.fail_required, empty_field);
                            }
                        }
                        else $(location).attr('href',fail_page);
                })
                .fail(function(data){
                    progress.modal('hide');
                    $(location).attr('href',fail_page);
                })
                .progress(function(data){
                    var label = (data.pcent == 100) ? 'Please wait ...':data.pcent+'%';
                    console.log('progress', data);
                    progress.find('.progress-bar')
                                .attr('aria-valuenow',data.pcent)
                                .html(label)
                                .width(data.pcent+'%');
                    console.log(display_size(data.loaded));
                    progress.find('.download-size').html(display_size(data.loaded));
                    progress.find('.total-size').html(display_size(data.total));
                });
        
        }
    });
    
    website.snippet.animationRegistry.form_builder_input_file =  website.snippet.Animation.extend({
        selector: ".input-file",
        start: function () {
            
            var self = this;
            
            self.$target.find('.btn-file :file').on('change', function() {
                
                 var input = $(this),
                  numFiles = input.get(0).files ? input.get(0).files.length : 1,
                  labels = '';
                  
                  $.each(input.get(0).files, function(index, value) {
                    if(labels.length) labels += ', ';
                       labels += value.name.replace(/\\/g, '/').replace(/.*\//, '');
                      
                  });
                  self.$target.find(':text').val(labels);
            });
        },
        
        stop: function () {
            this.$target.find('.btn-file :file').off('change');
        }
    });
    
    website.snippet.animationRegistry.form_builder_autocomplete =  website.snippet.Animation.extend({

        selector:'.form-field-search',
        start: function() {
            var plugin_list = (this.$target.find('.form-control').attr('data-multiple') == 'multiple') ? 'tags autocomplete arrow' : 'autocomplete arrow';
            var list = [];
            var assocList = [];
            
            this.$target.find('.wrap-options').children().each(function (i,child) {
                list[i] = {name:$(child).html()};
                assocList[$(child).html()] = $(child).val();
            });
            
            this.$target.find('textarea')
                .textext({
                    plugins : plugin_list,
                    ext : {
                        itemManager: {
                            itemToString: function(i)    {return i.name;},
                            stringToItem: function(str) {return {name:str,id:assocList[str]};}
                        }
                }})
                .bind('getSuggestions', function(e, data) {
                     var textext  = $(e.target).textext()[0],
                    query      = (data ? data.query : '') || '';
                    $(this).trigger('setSuggestions',
                                    { result : textext.itemManager().filter(list, query) });
                });
        }
    });
})();
