(function () {
    'use strict';

    var website = openerp.website;
    var _t = openerp._t;
    var ValidOption = false;
    var getModel = function(model_field) {

        var self   = this;
        var def    = $.Deferred();
        var form   = this.$target.closest('form');

        if(!model_field && !form.data('model')) return def.reject();
        if(model_field == form.data('model') && !form.data('fields') && form.data('not-lock'))  return def.resolve();

        form.data('not-lock',0);
        form.data('model', model_field);
        form.data('fields', {all:{},required:{}});
        new openerp.Model(openerp.website.session,"website.form")
        .call("get_authorized_fields", [form.data('model')], {context: website.get_context()}).then(function(data) {
            var i = 0;
            var j = 0;

            $.each(data, function(n, val) {
                var sel = val.selection || null;
                var rel = val.relation  || null;
                if(!form.data('fields')[val.type]) form.data('fields')[val.type] = {};
                form.data('fields')[val.type][n] = {name: n, label : val.string,relation : rel,selection : sel, type: val.type, required: val.required, help: val.help};
                form.data('fields').all[n] = form.data('fields')[val.type][n];
                if(val.required) form.data('fields').required[j++] = n;
            });

            self.notLock = 1;
            def.resolve();
    
        }).fail(function() {
            self.notLock = 1;
            def.reject();
        });
        return def;

    };

    
    website.add_template_file('/website_form_builder/static/src/xml/website.form.editor.wizard.template.xml');


        //------------------------------//
        //      Option Editor           //
        //------------------------------//
        // Manage an editable table     //
        // With events to edit options  //
        // for one2many and many2many   //
        // fields                       //
        //------------------------------//

    website.snippet.editFormFieldOptionEditor = openerp.Class.extend({

        table: null,
        lock: null,

        init: function(parent) {
            this.parent = parent;
        },
        //Enable the widget with parameters : 
        // wizard : wizard dom pointer
        // target: form field that need to be edit by the option editor
        // get : function needed to exctract data from the form field
        
        enable: function(wizard,target,get) {
            this.table = wizard.find('table');
            this.loadData(wizard,target,get);
            this.offAddField();
            this.onAddField();
        },
        //check all checkboxes
        checkAll: function(self) {
            return function() {
                var allBoxes = self.table.find('input');
                allBoxes.prop('checked',$(this).is(':checked'));
            };
        },
        //check number of checkbox checked to fix main checkbox
        checkAllStates: function(self) {
            return function() {
                var i=0,j=0;
                var checkAllBox  = self.table.find('th input');
                self.checked = !self.checked;
                self.table.find('input.delete').each(function(a,elem) {
                    if($(elem).is(':checked')) i++;
                    j++;
                });
                console.log(i,j);
                checkAllBox.prop("indeterminate", false);
                if(i == j)      checkAllBox.prop('checked', true);
                else if(!i)     checkAllBox.prop('checked', false);
                else            checkAllBox.prop("indeterminate", true);
            };
        },
        //enable events on the option editor to add or remove line
        onAddField: function() {
            var self = this;
            self.table.find('.last .option-label')  .on('keydown', self.tabEvent());
            self.table.find('td')                   .on('keyup', self.deleteIfEmpty);
            self.table.find('.last .option-value')  .on('keydown', self.addField(false));
            self.table.find('.o_form-editor-add')     .on('click',self.addField(true));
        },
        //disable events
        offAddField: function() {
            var self = this;
            self.table.find('.last .option-value')  .off('keydown');
            self.table.find('.last .option-value')  .on('keydown', self.tabEvent());
            self.table.find('.o_form-editor-add')     .off('click');
            self.table.find('td')                   .off('td');
        },
        //check if the line is empty before delete it
        deleteIfEmpty : function (e) {
            var parent = $(this).parent();
            var prev,label,value;
            var p_label = parent.find('.option-label');
            var p_value = parent.find('.option-value');
            
            if(!p_label.html().length && !p_value.html().length) {
                    if(parent.hasClass('last')) {
                        prev = parent.prev();
                        label = prev.find('.option-label').html();
                        value = prev.find('.option-value').html();
                        p_label.html(label);
                        p_value.html(value);
                        parent = prev;
                    }
                    parent.next().focus();
                    setTimeout(function() {
                        document.execCommand('selectAll',false,null);
                    },100);
                    parent.remove();
                }
        },
        //select the text when user press tab
        tabEvent: function () {
            return function(e) {
                if(e.keyCode === 9) {
                    $(this).focus();
                    setTimeout(function() {
                        document.execCommand('selectAll',false,null);
                    },100);
                }
            };
        },
        //get a template of a line of the table for other internal functions 
        fieldModel : function() {
            return openerp.qweb.render('webiste.form.editor.wizard.option.template');
        },
        //manage events to add a line on the table
        addField: function(button) {
            var self = this;
            return function(e) {
                if((e.keyCode === 9) || button) {
                    e.preventDefault();
                    var tb_line = $(self.fieldModel());
                    tb_line.find('input.delete').remove();
                    self.offAddField();
                    
                    self.table.find('.o_form-editor-add').remove();
                    self.table.find('.last').removeClass('last');
                    tb_line.find('a.delete').on('click',function(e) {
                            $(this).parent().parent().remove();
                    });
                    self.table.find('tbody').append(tb_line);
                    
                    self.table.find('.last .option-label').focus();
                    setTimeout(function() {
                        document.execCommand('selectAll',false,null);
                    },100);
                    self.onAddField();
                }
            };
        },
        //add options from the wizard to the form field 
        //target : container for options
        //type : the type of the form field to link templates
        //params: various parameters to edit custom fields on the template
        addOptions: function (target,type,params) {
            var self = this;
            return function() {
                var fullOptions = '';
                var j = 0;
                target.html(' ');
                self.table.find('tr').each(function(i,elem) {
                    var check = $(elem).find('input.delete');
                    var label = $(elem).find('.option-label').html();
                    var value = $(elem).find('.option-value').html();
                    
                    if(label && value)
                        if((label.length > 0) && (value.length > 0)) {
                            params.label = label;
                            params.value = value;
                            params.id    = params.id_label+'-'+j;
                            if(!check || !check.length) params.visible = '';
                            else if (check.is(':checked')) params.visible = '';
                            else params.visible = 'hidden';
                            j++;
                            fullOptions += openerp.qweb.render('website.form.editor.template.option.'+type,params);
                        }
                });
                
                target.append(fullOptions);
            };
        },
        //load 
        restore: function() {
            var tb_line = $(this.fieldModel());
            if(!this.table) return;
            var parent = this.table.find('tbody');
            tb_line.find('input.delete').remove();
            tb_line.find('a.delete').on('click',function(e) {
                    $(this).parent().parent().remove();
            });
            this.table.find('.o_tb-actions input').addClass('hidden');
            $(this.table.find('th')[1]).removeClass('hidden');
            parent.html('');
            parent.append(tb_line);
            this.offAddField();
            this.onAddField();
            
        },
        loadData: function (wizard,target, get) {
            var self = this;
            var tb_line = $(self.fieldModel());
            this.lock = (wizard.find('.form-select-field').val() != 'custom');
            if(this.lock)   {
                tb_line.find('a.delete').remove();
                tb_line.find('.option-value').addClass('hidden');
                $(this.table.find('th')[1]).addClass('hidden');
                this.table.find('.o_tb-actions input').removeClass('hidden');
            }
            else{
                tb_line.find('input.delete').remove();
                tb_line.find('.option-value').removeClass('hidden');
                $(this.table.find('th')[1]).removeClass('hidden');
                this.table.find('.o_tb-actions input').addClass('hidden');
            }
            var tb_last = tb_line.clone();
            var tb_append;
            var last = self.table.find('.last');
            var parent = self.table.find('tbody');
            var dataList = target.children();
            
            last.remove();
            parent.html('');
            tb_line = $(tb_line[0]);
            
            tb_line.removeClass('last');
            
            if(!dataList.length) {
                parent.append('<td colspan="3"><strong>'+_t('No Data')+'</strong></td>');
                return;
            }
            
            $.each(dataList,function (i,elem) {

                var option = get(elem);
                
                if(option.last && !self.lock) tb_append = tb_last.clone();
                else tb_append = tb_line.clone();
                
                tb_append.find('.option-label').html(option.label).on('keydown', self.tabEvent());
                tb_append.find('.option-value').html(option.value).on('keydown', self.tabEvent());
                if(!self.lock) tb_append.find('a.delete').on('click',function(e) {
                    $(this).parent().parent().remove();
                });
                else {
                    if(!$(elem).hasClass('hidden')) tb_append.find('input').prop('checked', true);
                    tb_append.find('.option-value').prop('contenteditable',false);
                }
                    
                parent.append(tb_append);
            
            });
            this.table.find('.o_tb-actions input').prop('checked',true)
                                                .on('click',this.checkAll(this));
            this.table.find('input.delete').on('click',this.checkAllStates(this));
            this.checkAllStates(this)();
        }
        
    });

    //////////////////////////
    //  Form Widget Editor  //
    //----------------------//
    // All functions to     //
    // edit snippet form    //
    //////////////////////////


    website.snippet.options.editForm = website.snippet.Option.extend({
        wizard: null,
        validate: function (DefferedForm) {
                var self = this;
                var model_sel = this.wizard.find('.form-select-action').val();

                this.$target.attr('data-model', model_sel);
                this.$target.attr('action','/website_form/'+model_sel);
                this.$target.attr('data-success',this.wizard.find('#success').val());
                this.$target.attr('data-fail',this.wizard.find('#fail').val());

                this.getModel(model_sel).then(function(){
                    var mail = self.wizard.find('.o_form-action-mailto textarea').val();
                    var selectedModelOption = self.wizard.find(':selected');

                    self.$target.attr('data-model-name', selectedModelOption.data('model-name'));
                    self.$target.attr('data-default-field', selectedModelOption.data('default-field'));

                    if(self.wizard.find('select').val() != 'mail.mail') DefferedForm.resolve();
                    else if(mail.length > 0) {
                        new openerp.Model(openerp.website.session,"res.partner")
                        .call("find_or_create",[mail], {context: website.get_context()}).then(function(id) {
                            console.log(id);
                            if(id) {
                                var hidden_email = self.$target.find('.hidden_email_website_form_editor');
                                
                                if(!hidden_email || !hidden_email.length)
                                    self.$target.append('<input type="hidden" class="hidden_email_website_form_editor form-data" name="recipient_ids" value="'+id+'" />');
                                else hidden_email.val(id);
                                DefferedForm.resolve();
                            }
                            else DefferedForm.reject();
                        })
                        .fail(function() {DefferedForm.reject();});
                    }

                    $('a[href=#snippet_form]')
                                        .parent()
                                        .addClass('active');
                    $('button[data-action=snippet]').trigger('click');
                    self.wizard.modal('hide');
                    
                    $('#oe_snippets')   .removeClass('hidden')
                                        .find('.active')
                                        .removeClass('active');
                    $('#oe_snippets').find('#snippet_form')
                                        .addClass('active');
                });
        },
        organizeForm: function() {
            if(this.wizard.find('select').val() == 'mail.mail')
                this.wizard.find('.o_form-action-mailto').removeClass('hidden');
            else
                this.wizard.find('.o_form-action-mailto').addClass('hidden');
        },
        
        execute: function (type, value, $li) {
            if (type == 'click') this.on_prompt();
        },
        
        loadData: function(){
            if(this.$target.data('model'))      this.wizard.find('#formEditor-select-action').val(this.$target.data('model'));
            if(this.$target.data('success'))    this.wizard.find('#success').val(this.$target.data('success'));
            if(this.$target.data('fail'))       this.wizard.find('#fail').val(this.$target.data('fail'));
            
        },
        on_prompt: function () {
            var self = this;
            var DefFormPopUp = $.Deferred();
            
            new openerp.Model(openerp.website.session,"website.form")
            .call("search_read", [[],['model_name','model_id','name','metadata_field_id']], {context: website.get_context()})

            .then(function(options_list) {
                var options = '';
                $.each(options_list, function(i,elem) {
                    options += '<option value="'+elem.model_name+'" data-model-name="'+elem.model_id[1]+'" data-default-field="'+elem.metadata_field_id[1]+'">'+elem.name+'</option>';
                });
                self.wizard = $(openerp.qweb.render('website.form.editor.wizard.template.modelSelection',{'options': options}));
                self.wizard.appendTo('body').modal({"keyboard" :true});
                self.loadData();
                
                self.wizard.find('.o_form-action-mailto').find('textarea')
                    .textext({  plugins: 'autocomplete arrow',
                                ext: {
                                    itemManager: {
                                        itemToString: function(item) {
                                            return item.email;
                                        }
                                    }
                                }})
                    .bind('getSuggestions', function(e,data) {
                        var _this = this;
                        new openerp.Model(openerp.website.session,"res.partner")
                        .call("search_read",[[['email', '=like', $(this).val()+'%']],['email']], { limit: 5, context: website.get_context()}).then(function(tlist) {
                            $(_this).trigger('setSuggestions', {result: tlist});
                        });
                    });
                
                self.organizeForm();
                self.wizard.find('select').on('change',_.bind(self.organizeForm,self));
                self.wizard.find('.validate').on('click',_.bind(self.validate,self,DefFormPopUp));
            });

            return DefFormPopUp;
        },
        drop_and_build_snippet: function() {
            var self = this;
            this._super();
            this.on_prompt().fail(function () {  self.editor.on_remove(); });
        },
        start : function () {
            this._super();
            this.getModel = getModel;
        },
        clean_for_save: function () {},
    });
    
    //////////////////////////
    // Fields Widget Editor //
    //----------------------//
    // All functions to     //
    // edit snippet fields  //
    //////////////////////////
    
    website.snippet.options.editFormField = website.snippet.Option.extend({
          model: null,
          fields: null,
          old_action: null,
          wizard: null,

        //-------------------------------
        //         Data loading
        //-------------------------------
        // Functions to load data from 
        // $target to wizard assistant
        // for each kind of form fields
        //-------------------------------
        
        
        // Get list of fields with RPC Call
        getFields: function(types) {
            console.log(arguments);
            var options = '';
            var field_name = this.$target.find('.form-data').attr('name');
            var all_fields = this.$target.parent().find('.form-data');
            var all_fields_name = [];
            var form = this.$target.closest('form');

            all_fields.each(function(i,val) {
                all_fields_name[i] = $(val).attr('name');
            });
            
            var field = form.data('fields').all[field_name];
            this.lockCheckboxMultiple(field);
            options += ((field != undefined) && (field != null)) ?
                    '<option selected="selected" value="'+field.name+'">'+field.label+'</option>':'';
            
            
            $.each(types, function (j,type) {
                if(form.data('fields')[type]){
                    $.each(form.data('fields')[type], function(i, val) {
                        if(val && $.inArray(val.name,all_fields_name))
                            options += '<option value="'+val.name+'">'+val.label+'</option>';
                    });
                }
            });
            
            this.wizard.find('.form-select-field').append(options);
        },

        lockCheckboxMultiple: function(field) {
            var multiple = this.wizard.find('.form-field-multiple');
            
            if(field === undefined) {
                    multiple.prop('disabled',false);
                    return false;
                }
                
            if( (field.type == 'many2many') ||
                (field.type == 'one2many')  ||
                (field.type == 'manyBinary2many') ) {
                 if(multiple) {
                     multiple.prop('checked',true);
                     multiple.prop('disabled','disabled');
                 }
            }else {
                if(multiple){
                     multiple.prop('checked',false);
                     multiple.prop('disabled','disabled');
                }
                if(!((field.type == 'many2one') || (field.type == 'selection'))) return false;
            }
            return true;
        },
        getValues: function (selectFields) {
            var target = function(data){
                return {     values:        data,
                                children:    function() {return this.values;}};
            };
                var self = this;
                var selected_field = selectFields.children(":selected").val();
                var form  = this.$target.closest('form');
                var field = form.data('fields').all[selected_field];
               
                this.lockCheckboxMultiple(field);
                
                if (!field) {
                    this.optionEditor.restore();
                    return;
                }
                
                if(field.relation && field.relation != 'ir.attachment') {
                    openerp.jsonRpc('/web/dataset/call_kw', 'call', {
                                    model:  field.relation,
                                    method: 'search_read',
                                    args:[[],['display_name']],
                                    kwargs:{"context": website.get_context()}
                                    
                        }).then(function (data) {
                            self.optionEditor.loadData(self.wizard,target(data), function(data) {
                                return {label: data.display_name, value: data.id, last: 0};
                            });
                        });
                }
                else if(field.selection) {
                    this.optionEditor.loadData(this.wizard,target(field.selection), function(data) {
                        return {label: data[1], value: data[0], last: 0};
                    });
                }
                this.wizard.find('.form-field-label').val(field.label);
                this.wizard.find('.form-field-required').prop('checked',field.required);
        },
        hiddenLoadData: function() {
            var field_list = [];
            var field_label_list = [];
            var label;
            //var tags = $.parseJSON(this.$target.find('input').val()) || [];
            var tagsZone = this.wizard.find('.form-field-value');

            this.$target.closest('form').find('.form-field').each(function(i,elem) {
                label = $(elem).find('label').html();
                if(label.length > 1) {
                    field_label_list.push($(elem).find('.form-data').attr('name'));
                    field_list.push(label);
                }
            });
          
            this.wizard.find('.field_name').html(_t('Hidden Field'));
            this.getFields(['integer', 'date','char','text','float']);
            
            
            tagsZone.textext({
                plugins : 'tags autocomplete arrow',
                ext : {
                    tags: {
                        renderTag: function(tag) {
                            var self = this;
                            var node = $(self.opts('html.tag'));
                            var value = field_label_list[field_list.indexOf(tag)];
                            node.find('.text-label').text(tag);
                            node.data('text-tag', value ? "@"+value : tag);
                            if(!value) node.find('.text-button').css('background-color','#ffffff');
                            return node;
                        }
                    }
                }
            })
            .bind('getSuggestions', function(e, data) {
                var textext  = $(e.target).textext()[0],
                query    = (data ? data.query : '') || '';
                $(this).trigger('setSuggestions',
                                { result : textext.itemManager().filter(field_list, query) });
            });
            /*
            .bind('ready', function(e,data){
                $.each(tags, function(i,elem) {
                    tagsZone.textext()[0].tags().addTags((elem[0] == '@') ? [elem.substring(1)]:[elem]);
                });
            });
*/
            this.wizard.find('.form-field-label').val(this.$target.find('.form-data').prop('name')).parent().parent().addClass('hidden');
            this.wizard.find('.form-field-required').parent().parent().addClass('hidden');
            this.wizard.find('.form-field-help').parent().parent().addClass('hidden');
           
        },
        inputLoadData: function() {
            this.wizard.find('.field_name').html(_t('Text Field'));
            this.getFields(['integer', 'date','char','text','float']);
            this.wizard.find('.form-field-append-check')        .prop('checked',(this.$target.find('.append').length > 0));
            this.wizard.find('.form-field-prepend-check')    .prop('checked',(this.$target.find('.prepend').length > 0));
            this.wizard.find('.form-field-append')            .val(this.$target.find('.append').html());
            this.wizard.find('.form-field-prepend')            .val(this.$target.find('.prepend').html());
        },
        textareaLoadData: function() {
            this.wizard.find('.field_name').html(_t('Textarea'));
            this.getFields(['char','text']);
            this.wizard.find('.form-field-placeholder')        .val(this.$target.find('.form-data').prop('placeholder'));        // Load placeholder on wizard
        },
        inputfileLoadData: function() {
            this.wizard.find('.field_name').html(_t('Uplad Field'));
            this.getFields(['binary','manyBinary2many','oneBinary2many']);
            this.wizard.find('.form-field-placeholder')        .val(this.$target.find('.form-data').prop('placeholder'));
            this.wizard.find('.form-button-label')            .val(this.$target.find('.browse-label').html());
            this.wizard.find('.form-field-multiple')        .prop('checked',this.$target.find('input[type=file]').attr('multiple') == "multiple");
        },
        searchLoadData: function() {
            var self = this;
            this.wizard.find('.field_name').html(_t('Autocomplete Field'));
            this.getFields(['many2one','one2many','many2many','selection']);
            this.wizard.find('.form-field-multiple').prop('checked',this.$target.find('.form-data').attr('data-multiple') == "multiple");
            
            self.optionEditor.enable(    this.wizard,
                                        this.$target.find('.wrap-options'),
                                        function (elem) {
                                            elem = $(elem);
                                            return {label : elem.html(), value : elem.val(), last: !$(elem).next().length};
                                        });
        },
        selectLoadData: function() {
            var self = this;
            this.wizard.find('.field_name').html(_t('Select Field'));
            this.getFields(['many2one','one2many','many2many','selection']);
            this.wizard.find('.form-field-multiple').prop('checked',self.$target.find('.form-data').attr('multiple') == "multiple");
            
            self.optionEditor.enable(    this.wizard,
                                        self.$target.find('.wrap-options'),
                                        function (elem) {
                                            elem = $(elem);
                                            return {label : elem.html(), value : elem.val(), last: !$(elem).next().length};
                                        });
        },
        checkboxLoadData: function() {
            this.wizard.find('.field_name').html(_t('Checkbox Field'));
            this.getFields(['one2many','many2many']);
            this.wizard.find('.form-field-inline').prop('checked',this.$target.find('.wrap-options label').hasClass('checkbox-inline'));
            
            this.optionEditor.enable(   this.wizard,
                                        this.$target.find('.wrap-options'),
                                        function (elem) {
                                            elem = $(elem);
                                            return {label : elem.find('.option').html(), value : elem.find('input[type=checkbox]').val(), last: !$(elem).next().length};
                                        });
        },
        radioLoadData: function() {
            this.wizard.find('.field_name').html(_t('Radio Field'));
            this.getFields(['many2one','selection']);
            this.wizard.find('.form-field-inline').prop('checked',this.$target.find('.wrap-options label').hasClass('checkbox-inline'));
            
            this.optionEditor.enable(   this.wizard,
                                        this.$target.find('.wrap-options'),
                                        function (elem) {
                                            elem = $(elem);
                                            return {label : elem.find('.option').html(), value : elem.find('input[type=radio]').val(), last: !$(elem).next().length};
                                        });
        },
        defaultLoadData: function () {        
            this.wizard.find('.form-field-label')           .val(this.$target.find('label').html());                              // Load label on this.wizard
            this.wizard.find('.form-field-placeholder')     .val(this.$target.find('.form-data').prop('placeholder'));            // Load placeholder on wizard
            this.wizard.find('.form-field-help')            .val(this.$target.find('.help-block').html());                        // Load help text on this.wizard
            this.wizard.find('.form-field-required')        .prop('checked',this.$target.find('.form-data').prop('required'));    // Check required option on this.wizard if enabled
            this.wizard.find('.form-select-field')          .val(this.$target.find('.form-data').attr('name'));                   // Load action on this.wizard
        },
        
        //------------------------------------
        //         Validate and Update form
        //------------------------------------
        // Functions to update form fields
        // from data on the wizard assistant
        //------------------------------------
        hiddenValidate: function() {
            this.$target.find('.form-data').val(this.wizard.find('input[type=hidden]').val());
            this.$target.find('.help-block').html('');
            this.$target.find('label').html('');
        },
        textareaValidate: function() {
            this.$target.find('.form-data').prop('placeholder',this.wizard.find('.form-field-placeholder').val());
        },
        inputfileValidate: function() {
            var multiple = this.wizard.find('.form-field-multiple').is(':checked') ? 'multiple': false;
            this.$target.find('.form-data').prop('placeholder',this.wizard.find('.form-field-placeholder').val());
            this.$target.find('.browse-label').html(this.wizard.find('.form-button-label').val());
            this.$target.find('input[type=file]').attr('multiple',multiple);
        },
        searchValidate: function() {
            var optionsSelector = this.$target.find('.wrap-options');
            var field_name      = this.wizard.find('.form-select-field').val();
            var name            = (field_name  == 'custom') ? $.trim(this.wizard.find('.form-field-label').val()) : field_name;
            var multiple        = this.wizard.find('.form-field-multiple').is(':checked') ? 'multiple': false;

            this.$target.find('.form-data').attr('data-multiple',multiple);
            this.optionEditor.addOptions(optionsSelector,'search',{id_label:''})();
            this.$target.find('.form-data').html('<textarea class="o_form-input-search" name="'+name+'" rows="1"></textarea>');
        },
        selectValidate: function() {
            var optionsSelector = this.$target.find('.wrap-options');
            var i = 0;
            var multiple = this.wizard.find('.form-field-multiple').is(':checked') ? 'multiple': false;
            this.$target.find('.form-data').attr('multiple',multiple);
            this.optionEditor.addOptions(optionsSelector,'select',{id_label:''})();
        },
        checkboxValidate: function () {
            var optionsSelector = this.$target.find('.wrap-options');
            var i = 0;
            var field_name = this.wizard.find('.form-select-field').val();
            var name = (field_name  == 'custom') ? $.trim(this.wizard.find('.form-field-label').val()) : field_name;
            this.optionEditor.addOptions(optionsSelector,'checkbox',{id_label:name})();
            if(this.wizard.find('.form-field-inline').is(':checked')) {
                this.$target.find('.wrap-options label').addClass('checkbox-inline');
                this.$target.find('.wrap-options div').addClass('div-inline');
            }
            else {
                this.$target.find('.wrap-options label').removeClass('checkbox-inline');
                this.$target.find('.wrap-options div').removeClass('div-inline');
            }                                            
        },
        radioValidate: function () {
            var optionsSelector = this.$target.find('.wrap-options');
            var i = 0;
            var field_name = this.wizard.find('.form-select-field').val();
            var name = (field_name  == 'custom') ? $.trim(this.wizard.find('.form-field-label').val()) : field_name;
            this.optionEditor.addOptions(optionsSelector,'radio',{id_label:name})();
            if(this.wizard.find('.form-field-inline').is(':checked')) {
                this.$target.find('.wrap-options label').addClass('checkbox-inline');
                this.$target.find('.wrap-options div').addClass('div-inline');
            }
            else {
                this.$target.find('.wrap-options label').removeClass('checkbox-inline');
                this.$target.find('.wrap-options div').removeClass('div-inline');
            }
        },
        inputValidate: function() {

                var append_t      = this.wizard.find('.form-field-append').val();
                var prepend_t     = this.wizard.find('.form-field-prepend').val();
                
                var append_exist  = (this.$target.find('.append').length > 0) ;
                var prepend_exist = (this.$target.find('.prepend').length > 0) ;
                
                var append_check  = (append_t.length > 0);
                var prepend_check = (prepend_t.length > 0);
                
                this.$target.find('.form-data').prop('placeholder',this.wizard.find('.form-field-placeholder').val());
                
                // Remove or add Append or Prepend text to the input
                if(!append_exist && append_check) {
                    this.$target.find('.wrap-unwrap').append('<span class="input-group-addon append">'+append_t+'</span>');
                    append_exist = true;
                }
                else if(append_exist && !append_check) {
                    this.$target.find('.append').remove();
                    append_exist = false;
                }
                
                if(!prepend_exist && prepend_check) {
                    this.$target.find('.wrap-unwrap').prepend('<span class="input-group-addon prepend">'+prepend_t+'</span>');
                    prepend_exist = true;
                }
                else if(prepend_exist && !prepend_check) {
                    this.$target.find('.prepend').remove();
                    prepend_exist = false;
                }
            
                if(!append_exist && !prepend_exist)    this.$target.find('.wrap-unwrap').removeClass('input-group');
                else if(append_exist || prepend_exist) this.$target.find('.wrap-unwrap').addClass('input-group');
            
        },
        defaultValidate: function () {
            var name,help;
            var field_name; // custom or variable name from model
            var required;
            
            ValidOption = true;
            field_name  = this.wizard.find('.form-select-field').val();
            
            // get name/id from label for custom or from field_name;
            name        = (field_name  == 'custom') ? $.trim(this.wizard.find('.form-field-label').val()) : field_name;
    
            required    = (this.wizard.find('.form-field-required').is(':checked')) ? true:false;
            help        = this.wizard.find('.form-field-help').val();
            
            this.$target.find('.form-data').attr('data-field',field_name);
            this.$target.find('.form-data').attr('id',name);
            
            this.$target.find('.form-data').attr('name',name);
            this.$target.find('.form-data').attr('data-cke-saved-name',name);
            this.$target.find('.form-data').prop('required',required);
            if(required)    this.$target.find('label').removeClass('o_light');
            else            this.$target.find('label').addClass('o_light');

            
            if(help.length > 0) {
                if(this.$target.find('.help-block').length)     this.$target.find('.help-block').html(help);
                else                                            this.$target.find('.form-data').parent().append('<p class="help-block">'+help+'</p>');
            }
            else this.$target.find('.help-block').remove();
            
            this.$target.find('.control-label').html(this.wizard.find('.form-field-label').val());
            $('#oe_snippets').removeClass('hidden');
            this.wizard.modal('hide');
        },
        
        confirm: function (DefferedForm) {
                if(ValidOption) DefferedForm.resolve();
                else             DefferedForm.reject();
        },
        
        execute: function (type, value, $li) {
            if (type == 'click') {
                var self = this;
                this.on_prompt();
            }
        },
        
        on_prompt: function () {
         
            var fieldWizardTemplate;
            var type = this.$target.attr('data-form');
            var form = this.$target.closest('form');
            var label_for_custom = (type == 'inputfile') ? _t('Attached to')+' '+ form.data('model-name') : _t('Concatenate to')+' '+form.data('default-field');
            this.model  = this.$target.closest('form[action*="/website_form/"]').data('model');
            this.fields = (this.$target.closest('form[action*="/website_form/"]').data('fields'));
            

            //try to load specific wizard option
            
            try {
                //template dynamic loading
                fieldWizardTemplate = openerp.qweb.render('website.form.editor.wizard.template.'+type);
                
                //concat default behavior with specific field behavior to validate and to update the field
                this.validate = function() {
                    this.defaultValidate();
                    this[type+'Validate']();
                };
                //concat default behavior with specific field behavior to load data on wizard
                this.loadData = function() {
                    this.defaultLoadData();
                    this[type+'LoadData']();
                };
            }
            //else, use default behavior
            catch(e) {
                fieldWizardTemplate = '';
                this.validate = this.defaultValidate;
                this.loadData = this.defaultLoadData;
            }
             // Load template
            this.wizard = $(openerp.qweb.render('website.form.editor.wizard.template.default',{custom_label: label_for_custom, subTemplate: fieldWizardTemplate}));

            //Load field datas  
            this.loadData();

            this.wizard.appendTo('body').modal({"keyboard" :true});
            
            var DefFormPopUp = $.Deferred();
            var selectFields = this.wizard.find('.form-select-field');
            selectFields.on('change',_.bind(this.getValues,this,selectFields));
            this.wizard.on('hide.bs.modal',_.bind(this.confirm, this, DefFormPopUp));
            this.wizard.find('.validate').on('click',_.bind(this.validate,this));

            return DefFormPopUp;
        },

        drop_and_build_snippet: function() {
            var self = this;
      
            this._super();
            this.getModel().then(function() {
                if(!self.$target.hasClass('form-init')){
                    self.on_prompt().fail(function () {self.editor.on_remove(); });
                }
            });
        },
        start : function () {

            var self = this;
            this.getModel = getModel;
            this.optionEditor = new website.snippet.editFormFieldOptionEditor(this);
            if(this.$target.data('form') == 'hidden') this.$target.addClass('website-form-editor-hidden-under-edit');
            this.getModel();
            this._super();
        },
        clean_for_save: function () {
            var type = this.$target.attr('data-form');
            var name = this.$target.find('.form-data').attr('name');
            this.$target.removeClass('has-error has-success has-warning has-feedback')
                        .find('.form-control-feedback').remove();
            if(this.$target.data('form') == 'hidden') this.$target.removeClass('website-form-editor-hidden-under-edit');
            if(type == 'search')
                  this.$target.find('.form-data').html('<textarea class="o_form-input-search" name="'+name+'" rows="1"></textarea>');
        },
    });

    website.EditorBar.include({
        save: function () {
            var form = $('main form');
            form.find('.form-builder-error-message').remove();
            var required_error = '';
            if(!form.data('model')) return this._super();
            if(!form.data('fields')) return this._super();
            
            form.removeClass('o_send-failed o_send-success');
            $.each(form.data('fields').required,function(i,name){
                var present = 0;
                form.find('.form-data').each(function(j,elem){
                    present = present || ($(elem).prop('name') == name);
                    console.log($(elem).prop('name'), name,($(elem).prop('name') == name));
                });
                if(required_error !== '') required_error += ', ';
                if(!present)  required_error += form.data('fields').all[name].label;
            });
            if(required_error) {
                var message = _t('Some required fields are not present on your form. Please add the following fields on your form : ') + required_error;
                form.prepend($(openerp.qweb.render('website.form.editor.error',{'message':message})));
   
                return;
            }
            this._super();

        }
    });
})();