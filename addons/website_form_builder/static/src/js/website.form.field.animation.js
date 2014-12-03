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
            'input[type=file]': function($field) {
                var args = {};
                var size = $field.prop('files').length;
                var self = this;
                $.each($field.prop('files'), function (i, val) {
                    args[$field.attr('name')+(($field.prop('files').length > 1)? '['+i+']':'')] = val;
                    self.file += 1;
                });
                console.log('really no files ????? ', self.file);
                return ($.isEmptyObject(args)) ? null:args;
                
            }
        };

    website.snippet.animationRegistry.form_builder_send = website.snippet.Animation.extend({
        selector: 'form[action*="/website_form/"]',
        start: function() {
            var self = this;
            this.$target.find('.o_send_button').on('click',function(e) {self.send(e);});
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
                this.file = 0;
                this.$target.find('.form-data').each(function(j,elem){
                    
                    for (var i in getDataForm) {
                        if($(elem).is(i)) {
                            field_value = getDataForm[i].call(self, $(elem));
                            if(field_value) {
                                _.extend(args,field_value);
                            }
                            else if($(elem).attr('required')) {
                                console.log($(elem));
                                fail_required.push($(elem).attr('name'));
                            }
                            else {
                                empty_field.push($(elem).attr('name'));
                            }
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

               if(!this.file) progress.addClass('hidden');

                var success_page = this.$target.data('success');
                var redirect     = this.$target.data('redirect');

                console.log(args);
                openerp.post('/website_form/'+model,args)
                .then(function(data) {
                        progress.modal('hide');
                        // if the data are not inserted on the DB and server dont return list of 
                        // bad fields, we display an error
               
                        if(!(data && (data.id || (data.fail_required && data.fail_required.length)))) {
                            console.log('error without list');
                            self.$target.find('.o_form-success').show(500)
                                        .parent().find('.form-group').hide(500)
                                        .closest('form').removeClass('o_send-success')
                                                        .addClass('o_send-fail');
                            return;
                        }

                        // if the server return a list of bad fields, show theses fields for users
                        if(data.fail_required && data.fail_required.length) {
                            console.log('error with list');
                            self.indicateRequired(data.fail_required, empty_field);
                            return;
                        }
                        console.log('no_error', success_page, redirect);
                        // if success, show success or redirect sync or redirect async following configuration 
                        if(success_page) {
                            success_page = '/website_form/thanks' + ((success_page[0] == '/')? '':'/') + success_page;
                            $(location).attr('href', success_page);
                        }
                        else {
                            self.$target.find('.o_form-success').show(500)
                                        .parent().find('.form-group').hide(500)
                                        .closest('form').removeClass('o_send-failed')
                                                        .addClass('o_send-success');
                        }
                })
                .fail(function(data){
                    progress.modal('hide');
                    self.$target.find('.o_form-success').show(500)
                                        .parent().find('.form-group').hide(500)
                                        .closest('form').removeClass('o_send-success')
                                                        .addClass('o_send-fail');
                })
                .progress(function(data){
                    var label = (data.pcent == 100) ? 'Please wait ...':data.pcent+'%';
                    progress.find('.progress-bar')
                                .attr('aria-valuenow',data.pcent)
                                .html(label)
                                .width(data.pcent+'%');
                    progress.find('.download-size').html(data.h_loaded);
                    progress.find('.total-size').html(data.h_total);
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
        selector:'select[autocomplete=on]',
        start: function() {
            if(this.$target.closest('[contenteditable=true]').length) return;

            this.$target.select2({
                'enable': true
            });

            this.$target.closest('.form-group').find('.select2-container').removeClass('form-data wrap-options');
        },
        stop: function() {
            this.$target.select2('destroy');
        }
    });

})();
