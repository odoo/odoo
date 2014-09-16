(function () {
    'use strict';

    var website = openerp.website;
    var _t = openerp._t;
		
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
			
			this.$target.find('textarea')	.textext({
														plugins : plugin_list,
														ext : {
											                itemManager: {
											                    itemToString: function(i){
											                        return i.name;
											                    },
											                    stringToItem: function(str) {
											                        return {name:str,id:assocList[str]};
											                    }
											                }
											               
											            }
													})
        									.bind	('getSuggestions', function(e, data) {
											            
											            var textext  = $(e.target).textext()[0],
                										query 	 = (data ? data.query : '') || '';

											            $(this).trigger(
											                'setSuggestions',
											                { result : textext.itemManager().filter(list, query) }
											            );
        									});
    
		}	
	});		
})();



 
