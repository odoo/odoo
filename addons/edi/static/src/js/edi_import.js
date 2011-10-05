
openerp.web.edi_import = function(openerp) {
var QWeb = new QWeb2.Engine();
openerp.web.EdiImport = openerp.web.WebClient.extend({

    init: function(element_id) {
        this._super(element_id);
    },
    start: function() {
        this._super();
    },
    do_import: function(){
        var self = this;
        self.rpc('/web/import_edi/import_edi_url', self.params, function(response){
            if (response.length) {
                $('<div>Import successful, click Ok to see the new document</div>').dialog({
                modal: true,
                title: 'Successful',
                buttons: {
                    Ok: function() {
                        $(this).dialog("close");
                        var action = {
	                		"res_model": response[0][0],
	                		"res_id": parseInt(response[0][1], 10),
	                        "views":[[false,"form"]],
	                        "type":"ir.actions.act_window",
	                        "view_type":"form",
	                        "view_mode":"form"
	                    }
			            action.flags = {
	                		search_view: false,
	                        sidebar : false,
	                        views_switcher : false,
	                        action_buttons : false,
	                        pager: false
                        }
			            var action_manager = new openerp.web.ActionManager(self);
		                action_manager.appendTo($("#oe_app"));
			            action_manager.start();
			            action_manager.do_action(action);
                       }
                    }
            
                });
            }
            else{
                $(QWeb.render("DialogWarning", "Sorry, Import is not successful.")).dialog({
                    modal: true,
                    buttons: {
                        Ok: function() {
                            $(this).dialog("close");
                        }
                    }
                });
            }        
        });
    },
	import_edi: function(edi_url) {
		var self = this;
		this.params = {};
        
		if(edi_url) this.params['edi_url'] = decodeURIComponent(edi_url);
		
		if (!this.session.db){
            this.start();
            this.session.on_session_valid.add_last(self.do_import);
           
        }
        else{
            self.do_import();
        }
    }
});
}
// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
