openerp.google_spreadsheet = function(instance) {
    var _t = instance.web._t;
    instance.web.FormView.include({
    	on_processed_onchange: function(result, processed) {
    		var self = this;
    		
    			var fields = self.fields;
		        _(result.selection).each(function (selection, fieldname) {
		            var field = fields[fieldname];
		            if (!field) { return; }
		            field.field.selection = selection;
		            field.values = selection;
		            field.renderElement(); 
		        });
    		return this._super(result, processed);
    	},
    });
    instance.board.AddToGoogleSpreadsheet = instance.web.search.Input.extend({
	    template: 'SearchView.addtogooglespreadsheet',
	    _in_drawer: true,
	    start: function () {
	        var self = this;
	        this.$el.on('click', 'h4', function(){
    		 	var view = self.view;
				var data = view.build_search_data();
				var model = view.model;
				var list_view = self.view.getParent().views['list'];
				var view_id = list_view ? list_view.view_id : false; 
		        var context = new instance.web.CompoundContext(view.dataset.get_context() || []);
		        var domain = new instance.web.CompoundDomain(view.dataset.get_domain() || []);
		        _.each(data.contexts, context.add, context);
		        _.each(data.domains, domain.add, domain);
		        domain = JSON.stringify(domain.eval());
		        var groupbys = instance.web.pyeval.eval('groupbys', data.groupbys).join(" ");
		        var view_id = view_id;
                var ds = new instance.web.DataSet(self, 'google.drive.config');
                ds.call('set_spreadsheet', [model, domain, groupbys, view_id]).done(function (res) {
        			if (res['url']){
            			window.open(res['url'], '_blank');
        			}
				});
	        });
	    },
	});
	instance.web.SearchViewDrawer.include({
	    add_common_inputs: function() {
	        this._super();
	        var vm = this.getParent().getParent();
	        if (vm.inner_action && vm.inner_action.views) {
	            (new instance.board.AddToGoogleSpreadsheet(this));
	        }
	    }
	});
};