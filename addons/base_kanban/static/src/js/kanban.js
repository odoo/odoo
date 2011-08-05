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
        this.element_id = element_id;
        this.group_by_field = false;
        this.domains = this.dataset.domain;
        this.contexts = this.dataset.context;
        this.group_by = false;
        this.destination_index = false;
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
                self.on_reload_kanban([{'records': records, 'value':false, 'header': false}]);
	        });
	    }
    },

    on_show_data: function(datas) {
        var self = this;
        this.all_records = [];
        var new_qweb = new QWeb2.Engine();
        new_qweb.add_template('<templates><t t-name="custom_template">' + this.template_xml + '</t></templates>')
		self.$element.html(QWeb.render("KanbanBiew", {"datas" :datas}));
		_.each(datas, function(data) {
	        _.each(data.records, function(record) {
	            self.$element.find("#data_" + record.id).append(new_qweb.render('custom_template', record));
	            self.all_records.push(record);
	        });
        });
        this.$element.find( ".oe_table_column " ).css("width", 99 / datas.length +"%");
		this.$element.find(".oe_column").sortable({
		    connectWith: ".oe_column",
		    start: function(event, ui) {
                self.destination_index = ui.item.index();
            },
		    stop: self.on_recieve_record,
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

    on_close_action: function(e) {
        $(e.currentTarget).parents('.record:first').remove();
    },

    on_recieve_record: function(event, ui) {
        var self = this;
        var from = ui.item.index(), to = ui.item.prev().index() || 0;
        this.flag = false;
        if(this.columns.sequence && self.destination_index != from){
	        var child_record = ui.item.parent().children();
	        var data, sequence=1, index = to;
	        child_record.splice(0, to);
	        if(to >= 0 && child_record) {
	            var record_id = child_record.attr('id').split("_");
	            if(record_id.length >= 2) {
		            _.each(this.all_records, function(record){
		                if(parseInt(record_id[1]) == record.id && record.sequence) {
		                    sequence = record.sequence;
		                }
		            });
	            }
	        }
	        _.each(child_record, function (child) {
	            var child_id = parseInt($(child).attr("id").split("_")[1]);
	            if(child_id) {
	                self.dataset.write(child_id, {sequence: sequence});
	                sequence++;
	                self.flag = true;
	            }
	        });
        }
        if(ui.item.attr("id") && this.group_by_field) {
            var value = ui.item.closest("td").attr("id")
            if(value) {
                var data_val = {};
                value = value.split("_")[1];
                if(value == 'false') {
                    value = false;
                }
                data_val[this.group_by_field] = value;
                this.dataset.write(parseInt(ui.item.attr("id").split("_")[1]), data_val);
                this.flag = true;
            }
        }
        if(this.flag) {
            this.do_actual_search(this.domains, this.contexts, this.group_by);
        }
        this.destination_index = false;
    },

    on_reload_kanban: function(datas){
        this.$element.find("#kanbanview").remove();
        this.on_show_data(datas);
    },

    do_search: function (domains, contexts, group_by) {
        var self = this;
        this.rpc('/base/session/eval_domain_and_context', {
            domains: domains,
            contexts: contexts,
            group_by_seq: group_by
        }, function (results) {
            self.contexts = results.context;
            self.domains = results.domain;
            self.group_by = results.group_by;
            self.do_actual_search(results.domain, results.context, results.group_by);
        });
    },

    do_actual_search: function (domain, context, group_by) {
        var self = this;

        this.group_by_field = false;

        self.dataset.context = context;
        self.dataset.domain = domain;
        this.groups = new openerp.base.DataGroup(this, this.model, domain, context, group_by || []);
        this.groups.list([],
            function (groups) {
                if (group_by.length >= 1) {
                    self.group_by_field = group_by[0];
                    self.do_render_group(groups);
                }
            },
            function (dataset) {
                self.dataset.read_slice(false, false, false, function(records) {
                    self.on_reload_kanban([{'records': records, 'value':false, 'header' : false}]);
                });
            }
        );

    },
    do_render_group : function(datagroups){
        this.columns = [];
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
                self.columns.push({"value" : group_value, "records": records, 'header':group_name});
                if (datagroups.length == self.columns.length) {
                    self.on_reload_kanban(self.columns);
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
