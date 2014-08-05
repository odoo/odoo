(function () {
    'use strict';

    var website = openerp.website;
    var _t = openerp._t;
	var ValidOption = false;
    website.snippet.options.editForm = website.snippet.Option.extend({
    	validate: function (FormDialog) {
    		return function () {
    			if(FormDialog.find('.form-action-mailto').val().length > 0) {
    				ValidOption = true;
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
            var self = this;
            
            var modalDialog = $('<div class="modal fade">'  
            					+'<div class="modal-dialog">'
	    							+'<div class="modal-content">'
    		  							+'<div class="modal-header">'
        									+'<button type="button" class="close" data-dismiss="modal"><span aria-hidden="true">&times;</span><span class="sr-only">Close</span></button>'
        									+'<h4 class="modal-title">Add a New Form</h4>'
      									+'</div>'
      									+'<div class="modal-body">'
        									+'<form class="form-horizontal" role="form">'
        										+'<div class="form-group"><label for="formEditor-select-action" class="col-md-3 col-sm-4 control-label">Action : </label>'
        										+'<div class="col-md-9 col-sm-8"><select class="form-control form-select-action" id="formEditor-select-action">'
        											+'<option value="mail">Send by e-mail</option>'
        										+'</select></div></div>'
        										+'<div class="form-group"><label for="formEditor-mailto" class="col-md-3 col-sm-4 control-label">E-mail : </label>'
        										+'<div class="col-md-9 col-sm-8"><input type="email" class="form-control form-action-mailto" id="formEditor-mailto" />'
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
							
			console.log(self.validate);
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
           // this.$target.addClass("hidden");
        },
    });
})();


