(function () {
    'use strict';

    var website = openerp.website;
    var _t = openerp._t;
	var ValidOption = false;
    website.snippet.options.editFormField = website.snippet.Option.extend({
    	validate: function (FormDialog) {
    		var self = this;
    		var name;
    		var field_name; // custom or variable name from model
    		var required;
    		return function () {

    			if(FormDialog.find('.form-field-label').val().length > 0) {
    				ValidOption = true;
    				field_name 	= FormDialog.find('.form-select-field').val();
    			
	    			// get name/id from label for custom or from field_name;
	    			name 		= (field_name  == 'custom') ? $.trim(FormDialog.find('.form-field-label').val()) : field_name;
	    			required 	= (FormDialog.find('.form-field-label').is(':checked')) ? true:false;
	    			
	    			self.$target.find('.form-control').attr('data-field',field_name);	
	    			self.$target.find('.form-control').attr('id',name); 
	    			self.$target.find('.form-control').attr('name',name); 
	    			self.$target.find('.form-control').prop('placeholder',FormDialog.find('.form-field-placeholder').val());
	    			self.$target.find('.form-control').prop('required',required);
	    			self.$target.find('.help-block').html(FormDialog.find('.form-field-help').val());
    				self.$target.find('label').html(FormDialog.find('.form-field-label').val());
    				$('#oe_snippets').removeClass('hidden');
    				FormDialog.modal('hide');
    			}
    		};
    	},
    	
    	confirm: function (DefferedForm) {
    		return function() {
    			if(ValidOption) DefferedForm.resolve();
    			else			{
    				DefferedForm.reject(); 
    			}
    		};
    	},
    	
        on_prompt: function () {
            var self 	= this;
            var label 	= self.$target.find('label').html();
            var name 	= self.$target.find('.form-control').attr('name');
            var placeh	= self.$target.find('.form-control').prop('placeholder');
            var help,help_t,help_a = ""; // help : help exist ?, help_t : help text, help_a : help field active or not‡
            
            console.log(self.$target.find('.form-control').prop('required'));
            
            var req 	= (self.$target.find('.form-control').prop('required') == true) ? "checked": "";
            if(self.$target.find('.help-block').length > 0) {
            	help 	= "checked";
            	help_t 	= self.$target.find('.help-block').html();
            } 
            else {
            	help_a  = "disabled";
            }
            
            var field_selected = self.$target.find('.form-control').attr('data-field');
            var modalDialog = $('<div class="modal fade">'  
            					+'<div class="modal-dialog">'
	    							+'<div class="modal-content">'
    		  							+'<div class="modal-header">'
        									+'<button type="button" class="close" data-dismiss="modal"><span aria-hidden="true">&times;</span><span class="sr-only">Close</span></button>'
        									+'<h4 class="modal-title">Add a New Field</h4>'
      									+'</div>'
      									+'<div class="modal-body">'
        									+'<form class="form-horizontal" role="form">'
        										+'<div class="form-group"><label for="formFieldEditor-select-action" class="col-md-3 col-sm-4 control-label">Field : </label>'
        										+'<div class="col-md-9 col-sm-8"><select class="form-control form-select-field" id="formFieldEditor-select-action">'
        											+'<option value="custom">Custom</option>'
        										+'</select></div></div>'
        										+'<div class="form-group"><label for="formFieldEditor-label" class="col-md-3 col-sm-4 control-label">Label : </label>'
        										+'<div class="col-md-9 col-sm-8"><input type="text" class="form-control form-field-label" id="formFieldEditor-label" value="'+label+'"/>'
        										+'</div></div>'
        										+'<div class="form-group"><label for="formFieldEditor-placeholder" class="col-md-3 col-sm-4 control-label">Placeholder : </label>'
        										+'<div class="col-md-9 col-sm-8"><input type="text" class="form-control form-field-placeholder" id="formFieldEditor-placeholder" value="'+placeh+'" />'
        										+'</div></div>'
        										+'<div class="form-group"><label for="formFieldEditor-helped" class="col-md-3 col-sm-4 control-label">Help : </label>'
        										+'<div class="col-md-9 col-sm-8"><input type="checkbox" class="form-field-required" id="formFieldEditor-required" '+req+' />'
        										+'</div></div>'
        										+'<div class="form-group"><label for="formFieldEditor-help" class="col-md-3 col-sm-4 control-label">Help Text : </label>'
        										+'<div class="col-md-9 col-sm-8"><input type="text" class="form-control form-field-help" id="formFieldEditor-help" />'
        										+'</div></div>'
        										+'<div class="form-group"><label for="formFieldEditor-required" class="col-md-3 col-sm-4 control-label">Required : </label>'
        										+'<div class="col-md-9 col-sm-8"><input type="checkbox" class="form-field-required" id="formFieldEditor-required" '+req+' />'
        										+'</div></div>'
        									+'</form>'
      									+'</div>'
      									+'<div class="modal-footer">'
      										+'<button type="button" class="btn btn-primary validate">Continue</button>'
        									+'<button type="button" class="btn cancel" data-dismiss="modal" aria-hidden="true">Cancel</button>'
									    +'</div>'
									+'</div>'
								+'</div>'
							+'</div>');
							
			modalDialog.appendTo('body').modal({"keyboard" :true});
			
			var DefFormPopUp = $.Deferred();
			
			modalDialog.find('.form-select').on('change',self.organizeForm);
			modalDialog.on('hide.bs.modal',self.confirm(DefFormPopUp));
			modalDialog.find('.validate').on('click',self.validate(modalDialog));

			return DefFormPopUp;
           /* return website.prompt({
                id: "editor_new_form",
                window_title: _t("Add a New Form"),
                select: _t("Action"),
             /*   init: function (field) {
                    return website.session.model('mail.group')
                            .call('name_search', ['', [['public','=','public']]], { context: website.get_context() });
               }, 
            }).then(function (mail_group_id) {
                //self.$target.attr("data-id", mail_group_id);
                alert('deferred resolved');
            });*/
        },
        drop_and_build_snippet: function() {
            var self = this;
            this._super();
            this.on_prompt().fail(function () {
                self.editor.on_remove();
            });
        },
        start : function () {
            var self = this;
            this.$el.find(".js_action_form_list").on("click", _.bind(this.on_prompt, this));
            this._super();
        },
        clean_for_save: function () {
            //this.$target.addClass("hidden");
        },
    });
})();


