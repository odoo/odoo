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
        var template_xml = '';

        _.each(data.fields_view.arch.children, function(child) {
            if (child.tag == "template"){
                template_xml = openerp.base.json_node_to_xml(child, true)
            }
        });

        if(template_xml){
            self.dataset.read_slice([], 0, false, function (records) {
                self.on_show_data(records, template_xml);
	        });
	    }
    },

    on_show_data: function(records, template_xml) {
        var self = this;
        var new_qweb = new QWeb2.Engine();
        new_qweb.add_template('<templates><t t-name="custom_template">' + template_xml + '</t></templates>')

		self.$element.html(QWeb.render("KanbanBiew", {"records" :records}));
        _.each(records, function(record) {
            self.$element.find("#data_" + record.id).append(new_qweb.render('custom_template', record));
        });

		this.$element.find(".column").sortable({
		    connectWith: ".column"
		});
		this.$element.find(".portlet").addClass("ui-widget ui-widget-content ui-helper-clearfix ui-corner-all")
		    .find(".portlet-header")
		        .addClass("ui-widget-header ui-corner-all")
		        .prepend( "<span class='ui-icon ui-icon-closethick'></span><span class='ui-icon ui-icon-minusthick'></span>")
		        .end()
		    .find( ".portlet-content" );

		this.$element.find(".portlet-header .ui-icon").click(function() {
		    $(this).toggleClass("ui-icon-minusthick").toggleClass("ui-icon-plusthick");
		    $(this).parents(".portlet:first").find(".portlet-content").toggle();
		});
		this.$element.find('.portlet .ui-icon-closethick').click(this.on_close_action);
		this.$element.find(".column").disableSelection();
		this.$element.find(".ui.item").css("background-color","#c3dAf9");

		//self.$element.find( ".column" ).css("width",column_width);
    },

    on_close_action: function(e) {
        $(e.currentTarget).parents('.portlet:first').remove();
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
