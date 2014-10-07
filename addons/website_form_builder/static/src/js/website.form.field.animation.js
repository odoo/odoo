(function () {
    'use strict';

    var website = openerp.website;
    var _t = openerp._t;
    website.add_template_file('/website_form_builder/static/src/xml/website.form.editor.wizard.template.xml');
	website.snippet.animationRegistry.editForm = website.snippet.Animation.extend({
		selector: ".editForm",
		start: function() {
			this.$target.find('button').on('click', this.send());
		},
		stop: function() {
			this.$target.find('button').off('click');
		},
		send: function() {
			var self = this;
			
			return function(e) {
				e.preventDefault();
				var model = self.$target.find('form').data('model');
				var args = {"context": openerp.website.get_context()};
				self.$target.find('.form-data').each(function(i,elem){
					
					if($(elem).find('input[type=radio]').length != 0) {
						var subelem = $(elem).find('input[type=radio]:checked');
						args[$(subelem).prop('name')] = subelem.val();
					} 
					else if ($(elem).find('.form-input-search').length != 0) {
						var extracted_data = $.parseJSON($(elem).find('textarea').textext()[0].hiddenInput().val());
						var name = $(elem).attr('name');
						var subargs = [];
						$.each(extracted_data, function (i, val) {
							subargs.push(val.id);
						});
						args[name] = subargs;
					}
					else if(($(elem).hasClass('multivalues'))) {
						var subargs = [];
						var name = '';
						$(elem).find('input').each(function (j,subelem) {
							name = $(subelem).prop('name');
							if($(subelem).is(':checked')) subargs.push($(subelem).val());
						});	
						args[name] = subargs; 	
					} else  args[$(elem).prop('name')] = ($(elem).val()) ? $(elem).val() : 0;
				});
				openerp.jsonRpc('/contactus/'+model, 'call', args).then(function (data) {
				    	if(data) {
				    		if(data.id) $(location).attr('href',"contactus_success");
				    		else {
				    			var i = 0;
				    			var field_required = null;
				    			var len = (data.fail_required != null) ? data.fail_required.length:0;
				    			var name = null;
				    			if(!len) $(location).attr('href',"contactus_fail");
				    			else self.$target.find('.form-field').each(function(i,elem){
				    				if(i < len) field_required = data.fail_required[i];
				    				name = $(elem).find('.form-data').prop('name');
				    			
				    				if(field_required == name){
				    					$(elem)	.addClass('has-error has-feedback').find('.form-data').parent()
				    						   	.append('<span class="glyphicon glyphicon-remove form-control-feedback"></span>');
				    					i= i+1;
				    				}else
				    					$(elem)	.addClass('has-success has-feedback').find('.form-data').parent()
				    							.append('<span class="glyphicon glyphicon-ok form-control-feedback"></span>');
				    				
				    			});
				    		}
				    	}
				});
			};
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
