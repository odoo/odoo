(function () {
    'use strict';

    var website = openerp.website;
    var _t = openerp._t;
	var ValidOption = false;
	var model = {
		ref : null,
		fields : null,
		notLock: 1,
		init: function(model_field) {
			var def = $.Deferred();
        	if((model_field != undefined) && (model_field != null)) {
        		if((model.ref == model_field) && (this.fields != null) && self.notLock) {
        			return def.resolve();
        		}
        		model.ref = model_field;
        		def.resolve();
        		return model.getFields();
        	}
        	return def.reject();
		},
		getFields : function() {
			var self = this;
			var def = $.Deferred();
			this.notLock = 0;
			
    		this.fields = {all:{},required:{}};
    		
    		(new openerp.Model(new openerp.Session(),"website.form"))
    		.call("get_authorized_fields", [this.ref], {context: openerp.website.get_context()}).then(function(data) {
    			var i = 0;
    			var j = 0;
				$.each(data, function(n, val) {
					var sel = (val.selection === undefined) ? null : val.selection;
					var rel = (val.relation === undefined) ? null : val.relation;
					if(self.fields[val.type] === undefined) self.fields[val.type] = {};
					self.fields[val.type][n] = {name: n, label : val.string,relation : rel,selection : sel, type: val.type, required: val.required, help: val.help};
					self.fields.all[n] = self.fields[val.type][n];
					if(val.required) self.fields.required[j++] = n; 
				});
				self.notLock = 1;
				def.resolve();
				
			}).fail(function() {
				self.notLock = 1;
				def.reject();
			});
			return def;
		}
	};
	
	website.add_template_file('/website_form_builder/static/src/xml/website.form.editor.wizard.template.xml');



	//////////////////////////
	//  Form Widget Editor  //
	//----------------------//
	// All functions to 	//
	// edit snippet form  	//
	//////////////////////////
	
	website.snippet.options.editForm = website.snippet.Option.extend({
		wizard: null,
    	validate: function () {
    		var self = this;
	
    		return function () {		
				var model_sel = self.wizard.find('.form-select-action').val();
				self.$target.find('form').attr('data-model', model_sel);
				self.$target.find('form').attr('action','/contactus/'+model_sel);
				
				model.ref = model_sel;
        		model.getFields().then(function(){
        			var mail = self.wizard.find('.form-action-mailto textarea').val();
        			if(self.wizard.find('select').val() != 'mail.mail') ValidOption = true;
    				else if(mail.length > 0) {
    					(new openerp.Model(new openerp.Session(),"website.form"))
    					.call("insert_partner",[mail], {context: openerp.website.get_context()}).then(function(id) {
    						console.log(id);
    						ValidOption = true;
    					});
    				}
    				$('#oe_snippets').removeClass('hidden');
    				self.wizard.modal('hide');
        		});	
    		};
    	},
    	
    	confirm: function (DefferedForm) {
    		return function() {
    			if(ValidOption) DefferedForm.resolve();
    			else			DefferedForm.reject();    		
    		};
    	},
    	organizeForm: function() {
    		if(this.wizard.find('select').val() == 'mail.mail')
    			this.wizard.find('.form-action-mailto').removeClass('hidden');
    		else 
    			this.wizard.find('.form-action-mailto').addClass('hidden');
    	},
        on_prompt: function () {
        	debugger;
            var self = this;
            var DefFormPopUp = $.Deferred();
            (new openerp.Model(new openerp.Session(),"website.form"))
    		.call("get_options_list", {context: openerp.website.get_context()}).then(function(options_list) {
    			var options = '';
    			$.each(options_list, function(i,elem) {
    				options += '<option value="'+elem.model+'">'+elem.label_option+'</option>';
    			});
    			
    			self.wizard = $(openerp.qweb.render('website.form.editor.wizard.template.modelSelection',{'options': options}));
				self.wizard.appendTo('body').modal({"keyboard" :true});
				  			
    			(new openerp.Model(new openerp.Session(),"website.form"))
    			.call("get_partners", {context: openerp.website.get_context()}).then(function(tlist) {
    				var plist = [];
    				$.each(tlist, function(i,elem) {if(elem) plist.push(elem);});
    				console.log(plist);
	    			self.wizard.find('.form-action-mailto').find('textarea')
	    			.textext({ plugins : 'autocomplete'})
	        		.bind('getSuggestions', function(e, data) {
	        			var list = plist,
					 	textext  = $(e.target).textext()[0],
	                	query 	 = (data ? data.query : '') || '';
						$(this).trigger('setSuggestions', { result : textext.itemManager().filter(list, query) });
	        		});
	       		});
        		

				
				self.wizard.find('select').on('change',_.bind(self.organizeForm,self));
				self.wizard.on('hide.bs.modal',self.confirm(DefFormPopUp));
				self.wizard.find('.validate').on('click',self.validate(self.wizard));
    		});

			return DefFormPopUp;
        },
        drop_and_build_snippet: function() {
            var self = this;
            this._super();
            this.on_prompt().fail(function () {  self.editor.on_remove(); });
        },
        start : function () {
        	debugger;
        	this.$el.find(".js_action_form_list").on("click", _.bind(this.on_prompt, this));
        	this._super();        
        },
        clean_for_save: function () {},
    });
    
    //////////////////////////
	// Fields Widget Editor //
	//----------------------//
	// All functions to 	//
	// edit snippet fields  //
	//////////////////////////
	
    website.snippet.options.editFormField = website.snippet.Option.extend({
  		model: null,
  		fields: null,
  		old_action: null,
  		wizard: null,
    	
    	//////////////////////////////////////
    	//----------------------------------//
    	// 		Subwidgets					//
    	//----------------------------------//
    	// Sub widgets to improve wizards 	//
    	//----------------------------------//
    	//////////////////////////////////////
    	
    	//------------------------------//
    	//		Option Editor			//
    	//------------------------------//
    	// Manage an editable table 	//
    	// With events to edit options	//
    	// for one2many and many2many	//
    	// fields						//
    	//------------------------------//
    	
    	
    	optionEditor : {
    		table: null,
    		lock: null,
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
    				if(i == j) 		checkAllBox.prop('checked', true);
    				else if(i == 0)	checkAllBox.prop('checked', false);
    				else			checkAllBox.prop("indeterminate", true);
    			};
    		},
    		//enable events on the option editor to add or remove line
    		onAddField: function() {
    			var self = this;
    			self.table.find('.last .option-label')	.on('keydown', self.tabEvent());
    			self.table.find('td')					.on('keyup', self.deleteIfEmpty);		
    			self.table.find('.last .option-value')	.on('keydown', self.addField(false));
    			self.table.find('.form-editor-add')		.on('click',self.addField(true));
    		},
    		//disable events
    		offAddField: function() {
    			var self = this;
    			self.table.find('.last .option-value')	.off('keydown');
    			self.table.find('.last .option-value')	.on('keydown', self.tabEvent());
    			self.table.find('.form-editor-add')		.off('click');
    			self.table.find('td')					.off('td');
    		},
    		//check if the line is empty before delete it
    		deleteIfEmpty : function (e) {
    			var parent = $(this).parent();
    			var prev,label,value;
    			var p_label = parent.find('.option-label');
    			var p_value = parent.find('.option-value');
    			
    			if(	(p_label.html().length == 0) 
	    					&& 	(p_value.html().length == 0) ) {
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
		    			
		    			self.table.find('.form-editor-add').remove();
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
	    				
	    				if(!(label === undefined)  && !(value === undefined)) 
	    					if((label.length > 0) && (value.length > 0)) {
	    						params.label = label;
	    						params.value = value;
	    						params.id	 = params.id_label+'-'+j;
	    						if((check == undefined) || (check.length == 0)) params.visible = '';
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
    			if(this.table == undefined) return;
    			var parent = this.table.find('tbody');
    			tb_line.find('input.delete').remove();
    			tb_line.find('a.delete').on('click',function(e) {
			    		$(this).parent().parent().remove();
			    });
			    this.table.find('.tb-actions input').addClass('hidden');
			    
    			parent.html('');
    			parent.append(tb_line);
    			this.offAddField();
    			this.onAddField();
    			
    		},
    		loadData: function (wizard,target, get) {
    			var self = this;
    			var tb_line = $(self.fieldModel());
    			this.lock = (wizard.find('.form-select-field').val() != 'custom');
    			if(this.lock)	{
    				tb_line.find('a.delete').remove();
    				this.table.find('.tb-actions input').removeClass('hidden');
    			}
    			else{
    				tb_line.find('input.delete').remove();
    				this.table.find('.tb-actions input').addClass('hidden');
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
		    	
				if(dataList.length == 0) {
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
    			this.table.find('.tb-actions input').prop('checked',true)
    												.on('click',this.checkAll(this));
    			this.table.find('input.delete').on('click',this.checkAllStates(this));
    		}
    	},
    	
    	
    	//-------------------------------
    	// 		Data loading
    	//-------------------------------
    	// Functions to load data from 
    	// $target to wizard assistant
    	// for each kind of form fields
    	//-------------------------------
    	
    	
    	// Get list of fields with RPC Call
    	getFields: function(types) {
    		
    		var options = '';
			var field_name = this.$target.find('.form-data').attr('name');
			var all_fields = this.$target.parent().find('.form-data');
			var all_fields_name = [];
			all_fields.each(function(i,val) {
				all_fields_name[i] = $(val).attr('name');
			});
			
			var field = model.fields.all[field_name];
			this.lockCheckboxMultiple(field);
			options += ((field != undefined) && (field != null)) ?
					'<option selected="selected" value="'+field.name+'">'+field.label+'</option>':'';
			
			
    		$.each(types, function (j,type) {
    			if(model.fields[type] != undefined){
					$.each(model.fields[type], function(i, val) {
							if((val != null) && ($.inArray(val.name,all_fields_name))) 
								options += '<option value="'+val.name+'">'+val.label+'</option>';
					});	
				}		
			}); 
			
			this.wizard.find('.form-select-field').append(options);	
	    },
	    /*
	    saveOldValue : function() {
	    	var self = this;
	    	return function() {
	    		self.old_action = self.wizard.find('.form-select-field').val();
	    	};
	    },*/
	    lockCheckboxMultiple: function(field) {
	    	var multiple = this.wizard.find('.form-field-multiple');
	    	
	    	if(field === undefined) {
	    			multiple.prop('disabled',false);
	    			return false;
	    		}
	    		
	    	if((field.type == 'many2many') || (field.type == 'one2many')) {		    	 
			     if(multiple != undefined)	{
			    	 	multiple.prop('checked',true);
			    	 	multiple.prop('disabled','disabled');
			     }
			}else { 
			    if(multiple != undefined)	{
			    	 multiple.prop('checked',false);
			    	 multiple.prop('disabled','disabled');
				}
			    if(!((field.type == 'many2one') || (field.type == 'selection'))) return false;
			}
			return true;
	    },
	    getValues: function () {
	    	var self = this;
	    	var target = function(data){
	    		return { 	values:		data,
				   	 		children:	function() {return this.values;}};
			};
	    	
	    	return function() {
	    		
	    		var selected_field = $(this).children(":selected").val();
	    		var field = model.fields.all[selected_field];
				/*if(self.old_action != 'custom') {		    			
					var old_field = model.fields.all[self.old_action];
					model.fields[old_field.type][self.old_action] = old_field;				    			
				}*/
	   		
	    		self.lockCheckboxMultiple(field);
	    		
		    	if (field == undefined) {
		    		self.optionEditor.restore();
		    		return;
		    	}
		    	
		    	if(field.relation) {
			    	openerp.jsonRpc('/web/dataset/call_kw', 'call', {
			    					model:  field.relation,
			    					method: 'search_read',
			    					args:[[],['display_name']],
			    					kwargs:{"context": openerp.website.get_context()}
			    					
			    		}).then(function (data) {
			    			self.optionEditor.loadData(self.wizard,target(data), function(data) {
						    	return {label: data.display_name, value: data.id, last: 0};
						    });
						    
			    		});
			    }
			    else if(field.selection) {
			    	self.optionEditor.loadData(self.wizard,target(field.selection), function(data) {
						return {label: data[1], value: data[0], last: 0};
					});
			    }
			    self.wizard.find('.form-field-label').val(field.label);
			    self.wizard.find('.form-field-help').val(field.help); 
			    self.wizard.find('.form-field-required').prop('checked',field.required); 
			};	    
	    },
	    hiddenLoadData: function() {
	    	this.getFields(['integer', 'date','char','text','float'],this.wizard);
	    	this.wizard.find('.form-field-value').val(this.$target.find('.form-data').val());
	    	this.wizard.find('.form-field-label').val(this.$target.find('.form-data').prop('name'));
	    },
    	inputLoadData: function() {
    		this.getFields(['integer', 'date','char','text','float'],this.wizard);
    		this.wizard.find('.form-field-append-check')		.prop('checked',(this.$target.find('.append').length > 0));
    		this.wizard.find('.form-field-prepend-check')	.prop('checked',(this.$target.find('.prepend').length > 0));
    		this.wizard.find('.form-field-append')			.val(this.$target.find('.append').html());
    		this.wizard.find('.form-field-prepend')			.val(this.$target.find('.prepend').html());
    	},
    	textareaLoadData: function() {
    		this.getFields(['char','text'],this.wizard);
    		this.wizard.find('.form-field-placeholder')		.val(this.$target.find('.form-data').prop('placeholder'));		// Load placeholder on wizard
    	},
    	inputfileLoadData: function() {
    		this.getFields(['binary'],this.wizard);
    		this.wizard.find('.form-field-placeholder')		.val(this.$target.find('.form-data').prop('placeholder'));
    		this.wizard.find('.form-button-label')			.val(this.$target.find('.browse-label').html());
    		this.wizard.find('.form-field-multiple')		.prop('checked',this.$target.find('input[type=file]').attr('multiple') == "multiple");
    	},
    	searchLoadData: function() {
    		var self = this;
    		this.getFields(['many2one','one2many','many2many','selection']);
    		this.wizard.find('.form-field-multiple').prop('checked',this.$target.find('.form-data').attr('data-multiple') == "multiple");
    		
    		self.optionEditor.enable(	this.wizard,
    									this.$target.find('.wrap-options'),
    									function (elem) {
    										elem = $(elem);
    										return {label : elem.html(), value : elem.val(), last: $(elem).next().length == 0};
    									});
    	},
    	selectLoadData: function() {
    		var self = this;
    		this.getFields(['many2one','one2many','many2many','selection']);
    		this.wizard.find('.form-field-multiple').prop('checked',self.$target.find('.form-data').attr('multiple') == "multiple");
    		
    		self.optionEditor.enable(	this.wizard,
    									self.$target.find('.wrap-options'),
    									function (elem) {
    										elem = $(elem);
    										return {label : elem.html(), value : elem.val(), last: $(elem).next().length == 0};
    									});
    	},
    	checkboxLoadData: function() {
    		this.getFields(['one2many','many2many']);
    		this.wizard.find('.form-field-inline').prop('checked',this.$target.find('.wrap-options label').hasClass('checkbox-inline'));
    		
    		this.optionEditor.enable(	this.wizard,
    									this.$target.find('.wrap-options'),
    									function (elem) {
    										elem = $(elem);
    										return {label : elem.find('.option').html(), value : elem.find('input[type=checkbox]').val(), last: $(elem).next().length == 0};
    									});
    	},
    	radioLoadData: function() {
    		this.getFields(['many2one','selection']);
    		this.wizard.find('.form-field-inline').prop('checked',this.$target.find('.wrap-options label').hasClass('checkbox-inline'));
    		
    		this.optionEditor.enable(	this.wizard,
    									this.$target.find('.wrap-options'),
    									function (elem) {
    										elem = $(elem);
    										return {label : elem.find('.option').html(), value : elem.find('input[type=radio]').val(), last: $(elem).next().length == 0};
    									});
    	},
    	defaultLoadData: function () {		
    		this.wizard.find('.form-field-label')			.val(this.$target.find('label').html());								// Load label on this.wizard
			this.wizard.find('.form-field-placeholder')		.val(this.$target.find('.form-data').prop('placeholder'));			// Load placeholder on wizard
   			this.wizard.find('.form-field-help')			.val(this.$target.find('.help-block').html());							// Load help text on this.wizard
   			this.wizard.find('.form-field-required')		.prop('checked',this.$target.find('.form-data').prop('required'));	// Check required option on this.wizard if enabled
            this.wizard.find('.form-select-field')			.val(this.$target.find('.form-data').attr('name'));			// Load action on this.wizard
    	},
    	
    	//------------------------------------
    	// 		Validate and Update form
    	//------------------------------------
    	// Functions to update form fields
    	// from data on the wizard assistant
    	//------------------------------------
    	hiddenValidate: function() {
    		var self = this;
    		return function() {
    			self.$target.find('.form-data').val(self.wizard.find('.form-field-value').val());
    		};
    	},
    	textareaValidate: function() {
    		var self = this;
    		return function() {
    			self.$target.find('.form-data').prop('placeholder',self.wizard.find('.form-field-placeholder').val());
    		};
    	},
    	inputfileValidate: function() {
    		var self = this;
    		return function() {
    			var multiple = self.wizard.find('.form-field-multiple').is(':checked') ? 'multiple': false;
    			self.$target.find('.form-data').prop('placeholder',self.wizard.find('.form-field-placeholder').val());
    			self.$target.find('.browse-label').html(self.wizard.find('.form-button-label').val());
    			self.$target.find('input[type=file]').attr('multiple',multiple);
    		};
    	},
    	searchValidate: function() {
    		var self = this;
    		var optionsSelector = self.$target.find('.wrap-options');
    		return function() {
    			var field_name= self.wizard.find('.form-select-field').val();
    			var name 	 = (field_name  == 'custom') ? $.trim(self.wizard.find('.form-field-label').val()) : field_name;
    			var multiple = self.wizard.find('.form-field-multiple').is(':checked') ? 'multiple': false;
    			self.$target.find('.form-data').attr('data-multiple',multiple);
    			self.optionEditor.addOptions(optionsSelector,'search',{id_label:''})();
    			
    			self.$target.find('.form-data').html('<textarea class="form-input-search" name="'+name+'" rows="1"></textarea>');
    		};
    	},
    	selectValidate: function() {
     		var self = this;
    		var optionsSelector = self.$target.find('.wrap-options');
    		var i = 0;
    		return function() {
    			var multiple = self.wizard.find('.form-field-multiple').is(':checked') ? 'multiple': false;
    			self.$target.find('.form-data').attr('multiple',multiple);
    			self.optionEditor.addOptions(optionsSelector,'select',{id_label:''})();
    		};
    	},
    	checkboxValidate: function () {
    		var self = this;
    		var optionsSelector = self.$target.find('.wrap-options');
    		var i = 0;
    		return function() {
    			var field_name 	= self.wizard.find('.form-select-field').val();
    			var name = (field_name  == 'custom') ? $.trim(self.wizard.find('.form-field-label').val()) : field_name;
    			self.optionEditor.addOptions(optionsSelector,'checkbox',{id_label:name})();
    			if(self.wizard.find('.form-field-inline').is(':checked')) {
    				self.$target.find('.wrap-options label').addClass('checkbox-inline');
    				self.$target.find('.wrap-options div').addClass('div-inline');
    			}
    			else {
    				self.$target.find('.wrap-options label').removeClass('checkbox-inline');
    				self.$target.find('.wrap-options div').removeClass('div-inline');	
    			}			
    		};
    												
    	},
    	radioValidate: function () {
    		var self = this;
    		var optionsSelector = self.$target.find('.wrap-options');
    		var i = 0;
    		return function() {
    			var field_name 	= self.wizard.find('.form-select-field').val();
    			var name = (field_name  == 'custom') ? $.trim(self.wizard.find('.form-field-label').val()) : field_name;
    			self.optionEditor.addOptions(optionsSelector,'radio',{id_label:name})();
    			if(self.wizard.find('.form-field-inline').is(':checked')) {
    				self.$target.find('.wrap-options label').addClass('checkbox-inline');
    				self.$target.find('.wrap-options div').addClass('div-inline');
    			}
    			else {
    				self.$target.find('.wrap-options label').removeClass('checkbox-inline');
    				self.$target.find('.wrap-options div').removeClass('div-inline');	
    			}			
    		};
    												
    	},
    	inputValidate: function() {
    		var self = this;
    		
    		return function() {
    			var append_t 	= self.wizard.find('.form-field-append').val();
    			var prepend_t	= self.wizard.find('.form-field-prepend').val();
    			
    			var append_exist 	= (self.$target.find('.append').length > 0) ;
    			var prepend_exist	= (self.$target.find('.prepend').length > 0) ;
    			
    			var append_check	= (append_t.length > 0);
    			var prepend_check	= (prepend_t.length > 0);
    			
    			self.$target.find('.form-data').prop('placeholder',self.wizard.find('.form-field-placeholder').val());
    			
    			// Remove or add Append or Prepend text to the input
    			if(!append_exist && append_check) {
    				self.$target.find('.wrap-unwrap').append('<span class="input-group-addon append">'+append_t+'</span>');
    				append_exist = true;
    			}
    			else if(append_exist && !append_check) {
    				self.$target.find('.append').remove();
    				append_exist = false;
    			}
    			
    			if(!prepend_exist && prepend_check) {
    				self.$target.find('.wrap-unwrap').prepend('<span class="input-group-addon prepend">'+prepend_t+'</span>');
    				prepend_exist = true;
    			}
    			else if(prepend_exist && !prepend_check) {
    				self.$target.find('.prepend').remove();
    				prepend_exist = false;
    			}
    		
    			if(!append_exist && !prepend_exist) 			self.$target.find('.wrap-unwrap').removeClass('input-group');
    			else if(append_exist || prepend_exist) 			self.$target.find('.wrap-unwrap').addClass('input-group');
    		
    		};
    	},
    	defaultValidate: function () {
    		var self = this;
    		var name,help;
    		var field_name; // custom or variable name from model
    		var required;
    		
    	
    		return function () {
    			if(self.wizard.find('.form-field-label').val().length > 0) {
    				ValidOption = true;
    				field_name 	= self.wizard.find('.form-select-field').val();
    				
	    			// get name/id from label for custom or from field_name;
	    			name 		= (field_name  == 'custom') ? $.trim(self.wizard.find('.form-field-label').val()) : field_name;
	    	
	    			required 	= (self.wizard.find('.form-field-required').is(':checked')) ? true:false;
	    			help		= self.wizard.find('.form-field-help').val();
					
	    			self.$target.find('.form-data').attr('data-field',field_name);	
	    			self.$target.find('.form-data').attr('id',name); 
	    			self.$target.find('.form-data').attr('name',name); 
	    			self.$target.find('.form-data').prop('required',required);
	    			
	    			if(help.length > 0) {
	    				if(self.$target.find('.help-block').length) 	self.$target.find('.help-block').html(help);	
	    				else 											self.$target.find('.form-data').parent().append('<p class="help-block">'+help+'</p>');	
	    			}
	    			else self.$target.find('.help-block').remove();
	    			
    				self.$target.find('.control-label').html(self.wizard.find('.form-field-label').val());
    				$('#oe_snippets').removeClass('hidden');
    				self.wizard.modal('hide');
    			}
    		};
    	},
    	
    	confirm: function (DefferedForm) {
    		return function() {
    			if(ValidOption) DefferedForm.resolve();
    			else 			DefferedForm.reject();
    		};
    	},
    	
        on_prompt: function () {
        	
            var self 	= this;
            var fieldWizardTemplate;
            var type = this.$target.attr('data-form');
            
            this.model  = this.$target.parent().data('model');
            this.fields = (this.$target.parent().data('fields'));
            
            //try to load specific wizard option
            
            try {
            	//template dynamic loading
            	fieldWizardTemplate = openerp.qweb.render('website.form.editor.wizard.template.'+type);
            	
            	//concat default behavior with specific field behavior to validate and to update the field
            	self.validate = function() {
            		
            		var defaultFunction = self.defaultValidate();
            		var customFunction = self[type+'Validate']();
            		
            		return function () {
            			defaultFunction();
            			customFunction();
            		};
            	};
            	//concat default behavior with specific field behavior to load data on wizard
            	self.loadData = function() {
            		self.defaultLoadData();
            		self[type+'LoadData']();
            	};            
            }
            //else, use default behavior
            catch(e) {
            	fieldWizardTemplate = '';
            	self.validate = self.defaultValidate;
            	self.loadData = self.defaultLoadData;
            }
           
            this.wizard = $(openerp.qweb.render('website.form.editor.wizard.template.default',{subTemplate: fieldWizardTemplate})); 	// Load template
            
            //Load field datas  
            self.loadData();

			this.wizard.appendTo('body').modal({"keyboard" :true});
			
			var DefFormPopUp = $.Deferred();
			this.wizard.find('.form-select-field').on('change',this.getValues());
											// .on('focus',this.saveOldValue());
			this.wizard.on('hide.bs.modal',self.confirm(DefFormPopUp));
			this.wizard.find('.validate').on('click',self.validate());

			return DefFormPopUp;
        },
        removeAction: function () {
 	/*
			var selected_field = this.wizard.find('.form-select-field').val();
			console.log(selected_field);
			if ((selected_field != undefined) && (selected_field != null) && (selected_field != 'custom')) {
				var field = model.fields.all[selected_field];
				console.log(field.type, field.name, model.fields[field.type][field.name]);
				model.fields[field.type][field.name] = null;
				console.log(field.type, field.name, model.fields[field.type][field.name]);
				console.log(model.fields); 
			}*/

        },
        drop_and_build_snippet: function() {
            var self = this;
            this._super();
            model.init(this.$target.parent().attr('data-model')).then(function() {
	            if(!self.$target.hasClass('form-init')){
		            self.on_prompt().fail(function () {self.editor.on_remove(); })
		            				.then(function() {self.removeAction(); });	   				
		        }
		    });
        },
        launcher : function() {
        	var self = this;
        	self.on_prompt().then(function() {self.removeAction(); });
        },
        start : function () {
        	
            var self = this;
            model.init(this.$target.parent().attr('data-model')).then(function() {
            	console.log(model);
	            self.$el.find(".js_action_form_list").on("click", _.bind(self.launcher, self));
	       });
	       this._super();
        },
        clean_for_save: function () {
        	var type = this.$target.attr('data-form');
        	if(type == 'search')
  				this.$target.find('.form-data').html('<textarea class="form-input-search" name="'+name+'" rows="1"></textarea>');
        },
    });
    
    website.EditorBar.include({
    	save: function () {
    		$('main form').find('.form-builder-error-message').remove();
    		var required_error = '';
    		if(model.fields == undefined) return this._super();
    		$.each(model.fields.required,function(i,name){
    			var present = 0;
    			$('main form').find('.form-data').each(function(j,elem){
    				present = present || ($(elem).prop('name') == name);
    				console.log($(elem).prop('name'), name,($(elem).prop('name') == name));
    			});
    			if(required_error != '') required_error += ', ';
    			if(!present)  required_error += model.fields.all[name].label;
    		});
    		if(required_error) {
    			var message = _t('Some required fields are not present on your form. Please add the following fields on your form : ') + required_error;
    			$('main form').prepend($(openerp.qweb.render('website.form.editor.error',{'message':message})));
   
    			return;
    		}
    		this._super();
    	}
    });
})();