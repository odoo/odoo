(function () {
    'use strict';

    var website = openerp.website;
    var _t = openerp._t;
	var ValidOption = false;
	website.add_template_file('/website/static/src/xml/website.form.editor.wizard.template.xml');
	

	
    website.snippet.options.editFormField = website.snippet.Option.extend({
  
    	
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
    		enable: function(table,target,get) {
    			this.table = table;
    			this.loadData(target,get);
    			this.offAddField();
    			this.onAddField();
    			
    		},
    		onAddField: function() {
    			var self = this;
    			self.table.find('.last .option-label')	.on('keydown', self.tabEvent());
    			self.table.find('td')					.on('keyup', self.deleteIfEmpty);		
    			self.table.find('.last .option-value')	.on('keydown', self.addField(false));
    			self.table.find('.form-editor-add')		.on('click',self.addField(true));
    		},
    		offAddField: function() {
    			var self = this;
    			self.table.find('.last .option-value')	.off('keydown');
    			self.table.find('.last .option-value')	.on('keydown', self.tabEvent());
    			self.table.find('.form-editor-add')		.off('click');
    			self.table.find('td')					.off('td');
    		},
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
    		
    		fieldModel : function() {
    			var self = this;
    			var last_line = self.table.find('.last');
		    	var tb_line = $(last_line.wrap('<div></div>').parent().html());
		    	last_line.unwrap();
		    	return tb_line;
    		},
    		
    		addField: function(button) {
    			var self = this;
    			return function(e) {
    				if((e.keyCode === 9) || button) {
	    				e.preventDefault();
	    				var tb_line = self.fieldModel();	
		    		
		    			self.offAddField();
		    			
		    			self.table.find('.last .form-editor-add').remove();
		    			self.table.find('.last').removeClass('last');
		    			
		    			self.table.append(tb_line);
		    			
		    			self.table.find('.last .option-label').focus();
		    			setTimeout(function() {
	    					document.execCommand('selectAll',false,null);
	    				},100);
		    			self.onAddField();
		    		}
	    		};
    		},
    		addOptions: function (target,type,params) {
    			var self = this;
    			return function() {
    				var fullOptions = '';
    				var j = 0;
    				target.html(' ');
	    			self.table.find('tr').each(function(i,elem) {
	    				
	    				var label = $(elem).find('.option-label').html();
	    				var value = $(elem).find('.option-value').html();
	    				
	    				if(!(label === undefined)  && !(value === undefined)) 
	    					if((label.length > 0) && (value.length > 0)) {
	    						params.label = label;
	    						params.value = value;
	    						params.id	 = params.id_label+'-'+j;
	    						j++;
	    						fullOptions += openerp.qweb.render('website.form.editor.template.option.'+type,params);
	    					}
	    			});
	    			
	    			target.append(fullOptions);
    			};
    		},
    		
    		loadData: function (target, get) {
    			var lastElem;
    			var self = this;
    			var tb_line = $(self.fieldModel());
    			var tb_last = tb_line.clone();
    			var tb_append;
    			var last = self.table.find('.last');
    			var parent = last.parent();
    			
    			console.log(tb_line);
    			last.remove();
    			
    			tb_line.find('.form-editor-add').remove();
		    	tb_line.removeClass('last');
		    	console.log(tb_line);
    			target.children().each(function (i,elem) {
    			
    				elem = $(elem);
  
	    			var option = get(elem);
	    			if(elem.next().length == 0) {
	    				tb_append = tb_last.clone();
	    				console.log('last');
	    			}
	    			
	    			else tb_append = tb_line.clone();
	    		
	    			tb_append.find('.option-label').html(option.label).on('keydown', self.tabEvent());
			    	tb_append.find('.option-value').html(option.value).on('keydown', self.tabEvent());
			    		
			    	parent.append(tb_append);
			  	
    			});
    		}
    	},
    	
    	
    	//-------------------------------
    	// 		Data loading
    	//-------------------------------
    	// Functions to load data from 
    	// $target to wizard assistant
    	// for each kind of form fields
    	//-------------------------------
    	
    	inputLoadData: function(wizard) {
    		var self = this;
    		wizard.find('.form-field-append-check')		.prop('checked',(self.$target.find('.append').length > 0));
    		wizard.find('.form-field-prepend-check')	.prop('checked',(self.$target.find('.prepend').length > 0));
    		wizard.find('.form-field-append')			.val(self.$target.find('.append').html());
    		wizard.find('.form-field-prepend')			.val(self.$target.find('.prepend').html());
    	},
    	textareaLoadData: function(wizard) {
    		var self = this;
    		wizard.find('.form-field-placeholder')		.val(self.$target.find('.form-control').prop('placeholder'));		// Load placeholder on wizard
    	},
    	inputfileLoadData: function(wizard) {
    		wizard.find('.form-field-placeholder')		.val(this.$target.find('.form-control').prop('placeholder'));
    		wizard.find('.form-button-label')			.val(this.$target.find('.browse-label').html());
    		wizard.find('.form-field-multiple')			.prop('checked',this.$target.find('input[type=file]').attr('multiple') == "multiple");
    		console.log('multiple_detected', this.$target.find('input[type=file]').attr('multiple') == "multiple");
    	},
    	searchLoadData: function(wizard) {
    		var self = this;
    		
    		wizard.find('.form-field-multiple').prop('checked',self.$target.find('.form-control').attr('data-multiple') == "multiple");
    		
    		self.optionEditor.enable(	wizard.find('table'),
    									self.$target.find('.wrap-options'),
    									function (elem) {
    										return {label : elem.html(), value : elem.val()};
    									});
    	},
    	selectLoadData: function(wizard) {
    		var self = this;
    		
    		wizard.find('.form-field-multiple').prop('checked',self.$target.find('.form-control').attr('multiple') == "multiple");
    		
    		self.optionEditor.enable(	wizard.find('table'),
    									self.$target.find('.wrap-options'),
    									function (elem) {
    										return {label : elem.html(), value : elem.val()};
    									});
    	},
    	checkboxLoadData: function(wizard) {
    		var self = this;
    		
    		wizard.find('.form-field-inline').prop('checked',self.$target.find('.wrap-options label').hasClass('checkbox-inline'));
    		
    		self.optionEditor.enable(	wizard.find('table'),
    									self.$target.find('.wrap-options'),
    									function (elem) {
    										return {label : elem.find('.option').html(), value : elem.find('input[type=checkbox]').val()};
    									});
    	},
    	radioLoadData: function(wizard) {
    		var self = this;
    		
    		wizard.find('.form-field-inline').prop('checked',self.$target.find('.wrap-options label').hasClass('checkbox-inline'));
    		
    		self.optionEditor.enable(	wizard.find('table'),
    									self.$target.find('.wrap-options'),
    									function (elem) {
    										return {label : elem.find('.option').html(), value : elem.find('input[type=radio]').val()};
    									});
    	},
    	defaultLoadData: function (wizard) {
    		
    		var self = this;
    		wizard.find('.form-field-label')			.val(self.$target.find('label').html());								// Load label on wizard
			wizard.find('.form-field-placeholder')		.val(self.$target.find('.form-control').prop('placeholder'));			// Load placeholder on wizard
   			wizard.find('.form-field-help')				.val(self.$target.find('.help-block').html());							// Load help text on wizard
   			wizard.find('.form-field-required')			.prop('checked',self.$target.find('.form-control').prop('required'));	// Check required option on wizard if enabled
            wizard.find('.form-select-field')			.val(self.$target.find('.form-control').attr('data-field'));			// Load action on wizard
    	},
    	
    	//------------------------------------
    	// 		Validate and Update form
    	//------------------------------------
    	// Functions to update form fields
    	// from data on the wizard assistant
    	//------------------------------------
    	
    	textareaValidate: function(wizard) {
    		var self = this;
    		return function() {
    			self.$target.find('.form-control').prop('placeholder',wizard.find('.form-field-placeholder').val());
    		};
    	},
    	inputfileValidate: function(wizard) {
    		var self = this;
    		return function() {
    			var multiple = wizard.find('.form-field-multiple').is(':checked') ? 'multiple': false;
    			self.$target.find('.form-control').prop('placeholder',wizard.find('.form-field-placeholder').val());
    			self.$target.find('.browse-label').html(wizard.find('.form-button-label').val());
    			self.$target.find('input[type=file]').attr('multiple',multiple);
    		};
    	},
    	searchValidate: function(wizard) {
    		var self = this;
    		var optionsSelector = self.$target.find('.wrap-options');
    		return function() {
    			var multiple = wizard.find('.form-field-multiple').is(':checked') ? 'multiple': false;
    			self.$target.find('.form-control').attr('data-multiple',multiple);
    			self.optionEditor.addOptions(optionsSelector,'search',{id_label:''})();
    		};
    	},
    	selectValidate: function(wizard) {
     		var self = this;
    		var optionsSelector = self.$target.find('.wrap-options');
    		var i = 0;
    		return function() {
    			var multiple = wizard.find('.form-field-multiple').is(':checked') ? 'multiple': false;
    			self.$target.find('.form-control').attr('multiple',multiple);
    			self.optionEditor.addOptions(optionsSelector,'select',{id_label:''})();
    		};
    	},
    	checkboxValidate: function (wizard) {
    		var self = this;
    		var optionsSelector = self.$target.find('.wrap-options');
    		var i = 0;
    		return function() {
    			self.optionEditor.addOptions(optionsSelector,'checkbox',{id_label:'check'})();
    			if(wizard.find('.form-field-inline').is(':checked')) {
    				self.$target.find('.wrap-options label').addClass('checkbox-inline');
    				self.$target.find('.wrap-options div').addClass('div-inline');
    			}
    			else {
    				self.$target.find('.wrap-options label').removeClass('checkbox-inline');
    				self.$target.find('.wrap-options div').removeClass('div-inline');	
    			}			
    		};
    												
    	},
    	radioValidate: function (wizard) {
    		var self = this;
    		var optionsSelector = self.$target.find('.wrap-options');
    		var i = 0;
    		return function() {
    			self.optionEditor.addOptions(optionsSelector,'radio',{id_label:'check'})();
    			if(wizard.find('.form-field-inline').is(':checked')) {
    				self.$target.find('.wrap-options label').addClass('checkbox-inline');
    				self.$target.find('.wrap-options div').addClass('div-inline');
    			}
    			else {
    				self.$target.find('.wrap-options label').removeClass('checkbox-inline');
    				self.$target.find('.wrap-options div').removeClass('div-inline');	
    			}			
    		};
    												
    	},
    	inputValidate: function(wizard) {
    		var self = this;
    		
    		return function() {
    			var append_t 	= wizard.find('.form-field-append').val();
    			var prepend_t	= wizard.find('.form-field-prepend').val();
    			
    			var append_exist 	= (self.$target.find('.append').length > 0) ;
    			var prepend_exist	= (self.$target.find('.prepend').length > 0) ;
    			
    			var append_check	= (append_t.length > 0);
    			var prepend_check	= (prepend_t.length > 0);
    			// Remove or add Append or Prepend text to the input
    			
 				self.$target.find('.form-control').prop('placeholder',wizard.find('.form-field-placeholder').val());
 				
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
    	defaultValidate: function (wizard) {
    		var self = this;
    		var name,help;
    		var field_name; // custom or variable name from model
    		var required;
    		
    	
    		return function () {
    			if(wizard.find('.form-field-label').val().length > 0) {
    				ValidOption = true;
    				field_name 	= wizard.find('.form-select-field').val();
    			
	    			// get name/id from label for custom or from field_name;
	    			name 		= (field_name  == 'custom') ? $.trim(wizard.find('.form-field-label').val()) : field_name;
	    			required 	= (wizard.find('.form-field-required').is(':checked')) ? true:false;
	    			help		= wizard.find('.form-field-help').val();
	    			
	    			
	    			if(!wizard.find('.form-field-helped').is(':checked')) {
						self.$target.find('.help-block').addClass("hidden");
					}
					else {
						self.$target.find('.help-block').removeClass("hidden");
					}
					
	    			self.$target.find('.form-control').attr('data-field',field_name);	
	    			self.$target.find('.form-control').attr('id',name); 
	    			self.$target.find('.form-control').attr('name',name); 
	    			self.$target.find('.form-control').prop('required',required);
	    			
	    			if(help.length > 0) {
	    				if(self.$target.find('.help-block').length) 	self.$target.find('.help-block').html(help);	
	    				else 											self.$target.find('.form-control').parent().append('<p class="help-block">'+help+'</p>');	
	    			}
	    			else self.$target.find('.help-block').remove();
	    			
    				self.$target.find('.control-label').html(wizard.find('.form-field-label').val());
    				$('#oe_snippets').removeClass('hidden');
    				wizard.modal('hide');
    			}
    		};
    	},
    	
    	confirm: function (DefferedForm) {
    		return function() {
    			if(ValidOption) DefferedForm.resolve();
    			else {
    				DefferedForm.reject(); 
    			}
    		};
    	},
    	
        on_prompt: function () {
        	
            var self 	= this;
            var fieldWizardTemplate;
            var type = this.$target.attr('data-form');
            
            //try to load specific wizard option
            console.log(type);
            try {
            	//template dynamic loading
            	fieldWizardTemplate = openerp.qweb.render('website.form.editor.wizard.template.'+type);
            	
            	//concat default behavior with specific field behavior to validate and to update the field
            	self.validate = function(wizard) {
            		
            		var defaultFunction = self.defaultValidate(wizard);
            		var customFunction = self[type+'Validate'](wizard);
            		
            		return function () {
            			defaultFunction();
            			customFunction();
            		};
            	};
            	//concat default behavior with specific field behavior to load data on wizard
            	self.loadData = function(wizard) {
            		self.defaultLoadData(wizard);
            		self[type+'LoadData'](wizard);
            	};            
            }
            //else, use default behavior
            catch(e) {
            	fieldWizardTemplate = '';
            	self.validate = self.defaultValidate;
            	self.loadData = self.defaultLoadData;
            }
           
            var wizard = $(openerp.qweb.render('website.form.editor.wizard.template',{subTemplate: fieldWizardTemplate})); 	// Load template
            
            //Load field datas  
            self.loadData(wizard);

			wizard.appendTo('body').modal({"keyboard" :true});
			
			var DefFormPopUp = $.Deferred();
			
			wizard.on('hide.bs.modal',self.confirm(DefFormPopUp));
			wizard.find('.validate').on('click',self.validate(wizard));

			return DefFormPopUp;
        },
        drop_and_build_snippet: function() {
            var self = this;
            this._super();
            if(!this.$target.hasClass('form-init')){
	            this.on_prompt().fail(function () {
	                self.editor.on_remove();
	            });
	          }
        },
        start : function () {
            var self = this;
            this.$el.find(".js_action_form_list").on("click", _.bind(this.on_prompt, this));
            this._super();
        },
        clean_for_save: function () {
  
        },
    });
})();