(function () {
    'use strict';

    var website = openerp.website;
    var _t = openerp._t;
    website.add_template_file('/website_form_builder/static/src/xml/website.form.editor.wizard.template.xml');

    /* 
		dict of selectors and associated functions to extract data from the form
    */

    var getDataForm = {
        	'input[type=text]': 	function($field) {return $field.attr('value') ? _.object([$field.attr('name')], [$field.attr('value')]) : null;},
        	'input[type=hidden]': 	function($field) {return getDataForm['input[type=text]'].call(this,$field);},
        	'textarea': 			function($field) {return getDataForm['input[type=text]'].call(this,$field);},
        	'select': 				function($field) {return getDataForm['input[type=text]'].call(this,$field);},
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

	website.snippet.animationRegistry.editForm = website.snippet.Animation.extend({
		selector: 'form[action*="/website_form/"]',
		start: function() {
			var self = this;
			this.$target.find('button').on('click',function(e) {self.send(e);});
		},
		stop: function() {
			this.$target.find('button').off('click');
		},
		check: function() {
			this.$target.find('.form-data').each(function(i,val){

			});
		},
		indicateRequired: function(fail_required,empty_fields) {
			console.log('required', fail_required);
			console.log('empty', empty_fields);
			var i = 0, j=0;
			var field_required = null;
			var empty_field = null;
			var name = null;
			var len = (fail_required != null) ? fail_required.length:0;
			this.$target.find('.form-field').each(function(k,elem){

				name 			= $(elem).find('.form-data').attr('name');
				field_required 	= fail_required.indexOf(name);
				empty_field    	= empty_fields.indexOf(name);
				fail_required   = _.without(fail_required,name);
				empty_fields    = _.without(empty_fields,name);
			
			    if(field_required >= 0){
					$(elem)	.addClass('has-error has-feedback').children('div')
				    		.append('<span class="glyphicon glyphicon-remove form-control-feedback"></span>');
				    i= i+1;
				}
				else if(empty_field >= 0){
					$(elem)	.addClass('has-warning has-feedback').children('div')
				    		.append('<span class="glyphicon glyphicon-warning-sign form-control-feedback"></span>');
				    j= j+1;
				}
				else $(elem).addClass('has-success has-feedback').children('div')
				    		.append('<span class="glyphicon glyphicon-ok form-control-feedback"></span>');
				    				
			});
		},
		send: function(e) {
				e.preventDefault();
				// if(!this.check()) return;
				var self 			= this;
				var fail_required 	= [];
				var empty_field		= [];
				var model 			= this.$target.data('model');
				var args  			= {"context": website.get_context()};
				var field_value;

				this.$target.find('.form-data').each(function(i,elem){
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
					var i=0;
					var newsize = size;
					while((newsize > 0) && (i < 4)) {
						i++;
						newsize = newsize >> 10;
					}
					newsize = size >> (i*10-10);
					switch(i) {
						case 2 : return newsize+' Ko';
						case 3 : return newsize+' Mo'; 
						case 4 : return newsize+' Go'; 
						default: return newsize+' o'; 
					}
				};

				var success_page = this.$target.data('success');
				var fail_page = this.$target.data('fail');

				openerp.post('/website_form/'+model,args)
				.then(function (data) {		
						progress.modal('hide');
				    	if(data) {
				    		var len = (data.fail_required != null) ? data.fail_required.length:0;
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
	
	website.snippet.animationRegistry.inputFile =  website.snippet.Animation.extend({
		selector: ".input-file",
		start: function () {
			
			var self = this;
			
			self.$target.find('.btn-file :file').on('change', function() {
				
 				var input = $(this),
      			numFiles = input.get(0).files ? input.get(0).files.length : 1,
      			labels = '';
      			
      			$.each(input.get(0).files, function(index, value) {
        			if(labels.length != 0) labels += ', ';
      				labels += value.name.replace(/\\/g, '/').replace(/.*\//, '');
      				
      			});
      			self.$target.find(':text').val(labels);
			});
		},
		
		stop: function () {
			this.$target.find('.btn-file :file').off('change');
		}
	});
	
	website.snippet.animationRegistry.inputSearch =  website.snippet.Animation.extend({
		
		selector:'.form-field-search',
		start: function() { 
			var plugin_list = (this.$target.find('.form-control').attr('data-multiple') == 'multiple') ? 'tags autocomplete' : 'autocomplete';
			var list = new Array();
			var assocList =new Array();
			
			this.$target.find('.wrap-options').children().each(function (i,child) {
				list[i] = {name:$(child).html()};
				assocList[$(child).html()] = $(child).val();
			});
			
			this.$target.find('textarea')	
				.textext({
					plugins : plugin_list,
					ext : {
						itemManager: {
							itemToString: function(i)	{return i.name;},
							stringToItem: function(str) {return {name:str,id:assocList[str]};}
						}	               
				}})
        		.bind('getSuggestions', function(e, data) {
				 	var textext  = $(e.target).textext()[0],
                	query 	 = (data ? data.query : '') || '';
					$(this).trigger('setSuggestions',
									{ result : textext.itemManager().filter(list, query) });
        		});
		}	
	});		
})();
