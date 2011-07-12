openerp.base_export = function(openerp) {
QWeb.add_template('/base_export/static/src/xml/base_export.xml');
openerp.base.views.add('export', 'openerp.base_export.Export');
openerp.base_export.Export = openerp.base.Controller.extend({

    init: function(session, dataset, views){
        this._super(session);
        this.dataset = dataset
        this.views = views

    },
    start: function() {
        this.rpc("/base_export/export/get_fields", {"model": this.dataset.model}, this.on_loaded);
    },
    on_loaded: function(result) {
        var self = this;
        var element_id = _.uniqueId("act_window_dialog");
        this._export = $('<div>', {id: element_id}).dialog({
            title: "Export Data",
            modal: true,
            width: '50%',
            height: 'auto',
            buttons : {
                        "Close" : function() {
                        this._export.dialog('destroy');
                          },
                        "Export To File" : function() {
                        this._export.dialog('destroy');
                          }
                       }
        }).html(QWeb.render('ExportTreeView'))
        self.on_show_data(result)
    },

    on_click: function(id, result) {
        var self = this
	    this.field_id = id.split("-")[1];
	    var model = ''
	    var prefix = ''
	    var name = ''
	    for (var record in result){
	        if(result[record]['id'] == this.field_id){
	            model = result[record]['params']['model']
	            prefix = result[record]['params']['prefix']
	            name = result[record]['params']['name']
	        }
	    }
	    if (model){
	       this.rpc("/base_export/export/get_fields", {"model": model, "prefix": prefix, "field_parent" : this.field_id, "name": name}, this.on_show_data, {});
        }
    },

    on_show_data: function(result) {
        var self = this;
        var current_tr = $("tr[id='treerow_" + self.field_id + "']");
        if (current_tr.length >= 1){
            current_tr.after(QWeb.render('ExportTreeView-Secondary', {'fields': result}));
        }
        else{
            jQuery(self._export).find('#left_field_panel').append(QWeb.render('ExportTreeView-Secondary',  {'fields': result}));
        }
        jQuery($.find('img[id ^= parentimg]')).click(function(){
            self.on_click(this.id, result);
        });
        jQuery($.find('[id^=export]')).dblclick(function(){
            self.add_field(this.id, this.text)
        });
    },

    add_field: function(id, string) {
		var field_list = $('#fields_list')
		field_id = id.split("-")[1];
		if ( !$("#fields_list option[value='" + field_id + "']").length){
	        field_list.append( new Option(string, field_id));
	    }
    },
});

};
