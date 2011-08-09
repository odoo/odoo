openerp.base_kanban = function (openerp) {
QWeb.add_template('/base_kanban/static/src/xml/base_kanban.xml');
openerp.base.views.add('kanban', 'openerp.base_kanban.KanbanView');
openerp.base_kanban.KanbanView = openerp.base.View.extend({

    init: function(parent, element_id, dataset, view_id) {
        this._super(parent, element_id);
        this.view_manager = parent;
        this.dataset = dataset;
        this.model = this.dataset.model;
        this.view_id = view_id;
        this.group_by_field = false;
        this.source_index = {};
        this.all_display_data = false;
        this.groups = [];
    },

    start: function() {
        this.rpc("/base_kanban/kanbanview/load",
        {"model": this.model, "view_id": this.view_id}, this.on_loaded);
    },
    on_loaded: function(data) {
        var self = this;
        this.template_xml = '';
        this.columns = data.all_fields;
        _.each(data.fields_view.arch.children, function(child) {
            if (child.tag == "template"){
                self.template_xml = openerp.base.json_node_to_xml(child, true)
            }
        });
        if(this.template_xml){
            self.dataset.read_slice([], 0, false, function (records) {
                self.all_display_data = [];
                self.all_display_data.push({'records': records, 'value':false, 'header': false});
                self.on_show_data(self.all_display_data);
	        });
	    }
    },

    on_show_data: function(datas) {
        var self = this;
        this.all_records = [];
        var new_qweb = new QWeb2.Engine();
		self.$element.html(QWeb.render("KanbanBiew", {"datas" :datas}));
        this.on_reload_kanban();
		this.$element.find(".oe_column").sortable({
		    connectWith: ".oe_column",
		    start: function(event, ui) {
                self.source_index['index'] = ui.item.index();
                self.source_index['column'] = ui.item.parent().attr('id');
            },
		    stop: self.on_recieve_record,
		});
        this.$element.find('button').click(function(){
            var record_id = $(this).closest(".record").attr("id");
            if(record_id) {
                record_id = parseInt(record_id.split("_")[1])
                if(record_id) {
                    if($(this).data("type") == "edit") {
                        self.do_edit(record_id);
                    }
                    if($(this).data("type") == "delete") {
                        self.do_delete(record_id);
                    }
                }
            }
        });

		this.$element.find(".record").addClass("ui-widget ui-widget-content ui-helper-clearfix ui-corner-all")
		    .find(".record-header")
		        .addClass("ui-widget-header ui-corner-all")
		        .prepend( "<span class='ui-icon ui-icon-closethick'></span><span class='ui-icon ui-icon-minusthick'></span>")
		        .end()
		    .find( ".record-content" );

		this.$element.find(".record-header .ui-icon").click(function() {
		    $(this).toggleClass("ui-icon-minusthick").toggleClass("ui-icon-plusthick");
		    $(this).parents(".record:first").find(".record-content").toggle();
		});
		this.$element.find('.record .ui-icon-closethick').click(this.on_close_action);
		this.$element.find(".oe_column").disableSelection();
    },

    do_edit: function(id){
        var self = this;
        this.flag = false;
        _.each(this.groups, function (group) {
            self.dataset.context = group.context;
            self.dataset.domain = group.domain;
            group.list([],
                function (groups) {},
                function (dataset) {
                    self.dataset.read_slice(false, false, false, function(records) {
                        var index = parseInt(_.indexOf(self.dataset.ids, id));
                        if(index >= 0) {
                            self.select_record(index);
                            self.flag = true;
                            return false;
                        }
                    });
                }
            );
            if(self.flag) {return false;}
        });
        if(!self.flag) {
            var index = parseInt(_.indexOf(self.dataset.ids, id));
            if(index >= 0) {self.select_record(index);}
        }
    },

    select_record:function (index) {
        if(this.view_manager) {
            this.dataset.index = index;
            this.view_manager.on_mode_switch('form');
        }
    },

    do_delete: function (id) {
        var self = this;
        return $.when(this.dataset.unlink([id])).then(function () {
            self.drop_records(id);
        });
    },

    drop_records: function (id) {
        var self = this;
        _.each(self.all_display_data, function(data, index) {
            _.each(data.records, function(record, index_row) {
                if(parseInt(record.id) == id) {
                    self.all_display_data[index]['records'].splice(index_row, 1)
                    return false;
                }
            });
        });
        self.$element.find("#main_" + id).remove()
    },

    on_close_action: function(e) {
        var record_id = $(e.currentTarget).parents('.record:first').attr("id")
        if(record_id) {
            record_id = parseInt(record_id.split("_")[1])
            if(record_id) {
                this.do_delete(record_id);
            }
        }
    },

    on_recieve_record: function(event, ui) {
        var self = this;
        var from = ui.item.index();
        this.flag = false;
        var to = ui.item.prev().index() || 0;
        if(!ui.item.attr("id")){
            return false;
        }
        if(self.columns.sequence && self.source_index.index && self.source_index.index != from) {
	        var child_record = ui.item.parent().children();
	        var data, sequence = 1, index = to;
	        child_record.splice(0, to);
	        if(to >= 0 && child_record) {
	            var record_id = child_record.attr('id').split("_");
	            if(record_id.length >= 2) {
		            _.each(self.all_records, function(record){
		                if(parseInt(record_id[1]) == record.id && record.sequence) {
		                    sequence = record.sequence;
		                    return false;
		                }
		            });
	            }
	        }
	        _.each(child_record, function (child) {
	            var child_id = parseInt($(child).attr("id").split("_")[1]);
	            if(child_id) {
	                _.each(self.all_display_data, function(data, index) {
	                    _.each(data.records, function(record, index_row) {
	                        if(parseInt(record.id) == child_id) {
	                            self.all_display_data[index]['records'][index_row]['sequence'] = sequence;
	                            return false;
	                        }
	                    });
	                });
	                self.dataset.write(child_id, {sequence: sequence});
	                sequence++;
	                self.flag = true;
	            }
	        });
        }
        if(self.group_by_field && self.source_index.column && self.source_index.column != ui.item.parent().attr('id')) {
            var value = ui.item.closest("td").attr("id")
            if(value) {
                var data_val = {};
                var wirte_id = parseInt(ui.item.attr("id").split("_")[1]);
                value = value.split("_")[1];
                if(value == 'false') {
                    value = false;
                }
                var update_record = false;
                _.each(self.all_display_data, function(data, index) {
                    _.each(data.records, function(record, index_row) {
                        if(parseInt(record.id) == wirte_id) {
                            self.all_display_data[index]['records'][index_row][self.group_by_field] = value;
                            update_record = self.all_display_data[index]['records'].splice(index_row,1)
                            return false;
                        }
                    });
                });
                _.each(self.all_display_data, function(data, index) {
                    if (data.value == value || (data.value == 'false' && value == false)) {
                        self.all_display_data[index]['records'].push(update_record[0]);
                    }
                });
                data_val[self.group_by_field] = value;
                self.dataset.write(wirte_id, data_val);
                self.flag = true;
            }
        }
        if(self.flag) {
            self.on_reload_kanban(this.all_display_data);
        }
        this.source_index = {};
    },

    on_reload_kanban: function(){
        var self = this;
        var new_qweb = new QWeb2.Engine();
        this.all_records = []
        new_qweb.add_template('<templates><t t-name="custom_template">' + this.template_xml + '</t></templates>')
        _.each(self.all_display_data, function(data, index) {
            if(data.records.length > 0){
                _.each(data.records, function(record) {
                    self.$element.find("#data_" + record.id).children().remove()
                    self.$element.find("#data_" + record.id).append(new_qweb.render('custom_template', record));
                    self.all_records.push(record);
	            });
            }
            else{
                self.$element.find("#column_" + data.value).remove();
                self.all_display_data.splice(index, 1);
            }
        });
        this.$element.find( ".oe_table_column " ).css("width", 99 / self.all_display_data.length +"%");
    },

    do_search: function (domains, contexts, group_by) {
        var self = this;
        this.rpc('/base/session/eval_domain_and_context', {
            domains: domains,
            contexts: contexts,
            group_by_seq: group_by
        }, function (results) {
	        self.group_by_field = false;
	        self.dataset.context = results.context;
	        self.dataset.domain = results.domain;
	        self.datagroup = new openerp.base.DataGroup(self, self.model, results.domain, results.context, results.group_by || []);
	        self.datagroup.list([],
	            function (groups) {
                    self.groups = groups;
	                if (group_by.length >= 1) {
	                    self.group_by_field = group_by[0].group_by;
	                    self.do_render_group(groups);
	                }
	            },
	            function (dataset) {
	                self.dataset.read_slice(false, false, false, function(records) {
	                    self.all_display_data = [];
	                    self.all_display_data.push({'records': records, 'value':false, 'header' : false});
	                    self.$element.find("#kanbanview").remove();
	                    self.on_show_data(self.all_display_data);
	                });
	            }
	        );

        });
    },

    do_render_group : function(datagroups){
        this.all_display_data = [];
        var self = this;
        _.each(datagroups, function (group) {
            self.dataset.context = group.context;
            self.dataset.domain = group.domain;
            var group_name = group.value;
            var group_value = group.value;
            if(!group.value) {
                group_name = "Undefined";
                group_value = 'false';
            }
            else if(group.value instanceof Array) {
                group_name = group.value[1]
                group_value = group.value[0]
            }
	        self.dataset.read_slice(false, false, false, function(records) {
                self.all_display_data.push({"value" : group_value, "records": records, 'header':group_name});
                if (datagroups.length == self.all_display_data.length) {
                    self.$element.find("#kanbanview").remove();
                    self.on_show_data(self.all_display_data);
	            }
	        });
        });
    },

    do_show: function () {
        this.$element.show();
    },

    do_hide: function () {
        this.$element.hide();
    },

});
};

// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
