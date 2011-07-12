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
	    var is_loaded = 0;
	    for (var record in result){
	        if(result[record]['id'] == this.field_id){
	            model = result[record]['params']['model']
	            prefix = result[record]['params']['prefix']
	            name = result[record]['params']['name']
	            if ( (result[record]['children']).length >= 1){
                    $(result[record]['children']).each (function(e, childid) {
                        if ($("tr[id='treerow_" + childid +"']").length > 0) {
                            if ($("tr[id='treerow_" + childid +"']").is(':hidden')) {
                                is_loaded = -1;
                            } else {
	                            is_loaded++;
	                        }
	                    }
	                });
	                if (is_loaded == 0) {
                        if ($("tr[id='treerow_" + this.field_id +"']").find('img').attr('src') == '/base/static/src/img/expand.gif') {
                            if (model){
                                this.rpc("/base_export/export/get_fields", {"model": model, "prefix": prefix, "field_parent" : this.field_id, "name": name}, function (result) {
                                    self.on_show_data(result, true);
                                });
                            }
                        }
	                } else if (is_loaded > 0) {
	                    self.showcontent(this.field_id, true);
	                } else {
	                    self.showcontent(this.field_id, false);
	                }
	            }
	        }
	    }
    },

    on_show_data: function(result, flag) {
        var self = this;
        var current_tr = $("tr[id='treerow_" + self.field_id + "']");
        if (current_tr.length >= 1){
            current_tr.find('img').attr('src','/base/static/src/img/collapse.gif');
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


    // show & hide the contents
    showcontent: function (id, flag) {
        var first_child = $("tr[id='treerow_" + id + "']").find('img')
        if (flag) {
            first_child.attr('src', '/base/static/src/img/expand.gif');
        }
        else {
            first_child.attr('src', '/base/static/src/img/collapse.gif');
        }
        var child_field = $("tr[id^='treerow_" + id +"/']")
        for (var i = 0; i < child_field.length; i++) {
            if (flag) {
                $(child_field[i]).hide();
            }
            else {
                $(child_field[i]).show();
            }
        }
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
