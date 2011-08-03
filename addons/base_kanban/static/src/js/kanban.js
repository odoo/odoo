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
    },

    start: function() {
        this.rpc("/base_kanban/kanbanview/load",
        {"model": this.model, "view_id": this.view_id}, this.on_loaded);
    },
    on_loaded: function(data) {
        var self = this;
        this.template_xml = '';

        _.each(data.fields_view.arch.children, function(child) {
            if (child.tag == "template"){
                self.template_xml = openerp.base.json_node_to_xml(child, true)
            }
        });
        if(this.template_xml){
            self.dataset.read_slice([], 0, false, function (records) {
                self.on_show_data([{'records': records, 'value':false}]);
	        });
	    }
    },

    on_show_data: function(datas) {
        var self = this;
        var new_qweb = new QWeb2.Engine();
        new_qweb.add_template('<templates><t t-name="custom_template">' + this.template_xml + '</t></templates>')
		self.$element.html(QWeb.render("KanbanBiew", {"datas" :datas}));
		_.each(datas, function(data) {
	        _.each(data.records, function(record) {
	            self.$element.find("#data_" + record.id).append(new_qweb.render('custom_template', record));
	        });
        });

		this.$element.find(".oe_column").sortable({
		    connectWith: ".oe_column"
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
		self.$element.find( ".oe_column" ).css("width", 99 / datas.length +"%");
    },

    on_close_action: function(e) {
        $(e.currentTarget).parents('.record:first').remove();
    },

    do_search: function (domains, contexts, group_by) {
        var self = this;
        this.rpc('/base/session/eval_domain_and_context', {
            domains: domains,
            contexts: contexts,
            group_by_seq: group_by
        }, function (results) {
            self.dataset.context = results.context;
            self.dataset.domain = results.domain;
            self.groups = new openerp.base.DataGroup(
                self, self.model, results.domain, results.context, results.group_by);
	        self.groups.list([],
	            function (groups) {
                    self.do_render_group(groups);
	            },
	            function (dataset) {
                    self.dataset.read_slice(false, false, false, function(records) {
                        self.on_show_data([{'records': records, 'value':false}]);
                    });
                });
        });
    },

    do_render_group : function(datagroups){
        this.columns = [];
        var self = this;
        _.each(datagroups, function (group) {
            self.dataset.context = group.context;
            self.dataset.domain = group.domain;
            var group_name = group.value;
            if(!group_name) {
                group_name = "Undefined"
            }
            else if(group_name instanceof Array) {
                group_name = group_name[1]
            }
	        self.dataset.read_slice(false, false, false, function(records) {
                self.columns.push({"value" : group_name, "records": records});
                if (datagroups.length == self.columns.length) {
                    self.on_show_data(self.columns);
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
