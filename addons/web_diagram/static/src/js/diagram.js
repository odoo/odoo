/*---------------------------------------------------------
 * OpenERP diagram library
 *---------------------------------------------------------*/

openerp.web_diagram = function (instance) {
var QWeb = instance.web.qweb,
      _t = instance.web._t,
     _lt = instance.web._lt;
instance.web.views.add('diagram', 'instance.web.DiagramView');
instance.web.DiagramView = instance.web.View.extend({
    display_name: _lt('Diagram'),
    searchable: false,
    init: function(parent, dataset, view_id, options) {
        this._super(parent);
        this.set_default_options(options);
        this.view_manager = parent;
        this.dataset = dataset;
        this.model = this.dataset.model;
        this.view_id = view_id;
        this.domain = this.dataset._domain || [];
        this.context = {};
        this.ids = this.dataset.ids;
    },
    start: function() {
        return this.rpc("/web_diagram/diagram/load", {"model": this.model, "view_id": this.view_id}, this.on_loaded);
    },

    toTitleCase: function(str) {
        return str.replace(/\w\S*/g, function(txt){return txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase();});
    },

    on_loaded: function(result) {

        var self = this;
        if(this.ids && this.ids.length) {
            this.id = this.ids[self.dataset.index || 0];
        }

        this.fields_view = result.fields_view,
        this.view_id = this.fields_view.view_id,
        this.fields = this.fields_view.fields,
        this.nodes = this.fields_view.arch.children[0],
        this.connectors = this.fields_view.arch.children[1],
        this.node = this.nodes.attrs.object,
        this.connector = this.connectors.attrs.object;

        this.$element.html(QWeb.render("DiagramView", this));
        this.$element.addClass(this.fields_view.arch.attrs['class']);

        this.$element.find('div.oe_diagram_pager button[data-pager-action]').click(function() {
            var action = $(this).data('pager-action');
            self.on_pager_action(action);
        });
        this.labels = _.filter(this.fields_view.arch.children, function(label){ 
        	return label.tag == "label" ;
          });

        this.do_update_pager();

        // New Node,Edge
        this.$element.find('#new_node.oe_diagram_button_new').click(function(){self.add_node();});

        if(this.id) {
            self.get_diagram_info();
        }

    },

    get_diagram_info: function() {
        var self = this;
        var params = {
            'id': this.id,
            'model': this.model,
            'node': this.node,
            'connector': this.connector,
            'bgcolor': this.nodes.attrs.bgcolor,
            'shape': this.nodes.attrs.shape,
            'src_node': this.connectors.attrs.source,
            'des_node': this.connectors.attrs.destination,
            'label': this.connectors.attrs.label || false,
            'visible_nodes': [],
            'invisible_nodes': [],
            'node_fields': [],
            'connectors': [],
            'connectors_fields': []
        };

        _.each(this.nodes.children, function(child) {
            if(child.attrs.invisible == '1')
                params['invisible_nodes'].push(child.attrs.name);
            else {
                params['visible_nodes'].push(child.attrs.name);
                params['node_fields'].push(self.fields[child.attrs.name]['string']|| this.toTitleCase(child.attrs.name));
            }
        });

        _.each(this.connectors.children, function(conn) {
            params['connectors_fields'].push(self.fields[conn.attrs.name]['string']|| this.toTitleCase(conn.attrs.name));
            params['connectors'].push(conn.attrs.name);
        });

        this.rpc(
            '/web_diagram/diagram/get_diagram_info',params,
            function(result) {
                self.draw_diagram(result);
            }
        );
    },

    get_label : function(){
    	var self = this
    	if(self.$element.find('.oe_diagram_diagram_header').text() == ""){
	    	_.each(self.labels,function(label){
	    		html_label = "<p>" + label.attrs.string + "</p>"
		    	self.$element.find('.oe_diagram_diagram_header').append(html_label)
		    	self.$element.find('.oe_diagram_diagram_header > p').css('padding-left','5px')
	    	})
    	}
    },

    on_diagram_loaded: function(record) {
        var id_record = record['id'];
        if(id_record) {
            this.id = id_record;
            this.get_diagram_info();
            this.get_label();
        }
    },

    // Set-up the drawing elements of the diagram
    draw_diagram: function(result) {
        var self = this;
        var res_nodes  = result['nodes'];
        var res_edges  = result['conn'];
        this.parent_field = result.parent_field;
        this.$element.find('h3.oe_diagram_title').text(result.name);

        var id_to_node = {};


        var style = {
            edge_color: "#A0A0A0",
            edge_label_color: "#555",
            edge_label_font_size: 10,
            edge_width: 2,
            edge_spacing: 100,
            edge_loop_radius: 100,

            node_label_color: "#333",
            node_label_font_size: 12,
            node_outline_color: "#333",
            node_outline_width: 1,
            node_selected_color: "#0097BE",
            node_selected_width: 2,
            node_size_x: 110,
            node_size_y: 80,
            connector_active_color: "#FFF",
            connector_radius: 4,
            
            close_button_radius: 8,
            close_button_color: "#333",
            close_button_x_color: "#FFF",

            gray: "#DCDCDC",
            white: "#FFF",
            
            viewport_margin: 50
        };

        // remove previous diagram
        var canvas = self.$element.find('div.oe_diagram_diagram')
                             .empty().get(0);

        var r  = new Raphael(canvas, '100%','100%');

        var graph  = new CuteGraph(r,style,canvas.parentNode);
        
        var confirm_dialog = $('#dialog').dialog({ 
            autoOpen: false,
            title: _t("Are you sure?") });
        

        _.each(res_nodes, function(node) {
            var n = new CuteNode(
                graph,
                node.x + 50,  //FIXME the +50 should be in the layout algorithm
                node.y + 50,
                CuteGraph.wordwrap(node.name, 14),
                node.shape === 'rectangle' ? 'rect' : 'circle',
                node.color === 'white' ? style.white : style.gray);

            n.id = node.id;
            id_to_node[node.id] = n;
        });

        _.each(res_edges, function(edge) {
            var e =  new CuteEdge(
                graph,
                CuteGraph.wordwrap(edge.signal, 32),
                id_to_node[edge.s_id],
                id_to_node[edge.d_id] || id_to_node[edge.s_id]  );  //WORKAROUND
            e.id = edge.id;
        });

        CuteNode.double_click_callback = function(cutenode){
            self.edit_node(cutenode.id);
        };
        var i = 0;
        CuteNode.destruction_callback = function(cutenode){
            if(!confirm(_t("Deleting this node cannot be undone.\nIt will also delete all connected transitions.\n\nAre you sure ?"))){
                return $.Deferred().reject().promise();
            }
            return new instance.web.DataSet(self,self.node).unlink([cutenode.id]);
        };
        CuteEdge.double_click_callback = function(cuteedge){
            self.edit_connector(cuteedge.id);
        };

        CuteEdge.creation_callback = function(node_start, node_end){
            return {label:_t("")};
        };
        CuteEdge.new_edge_callback = function(cuteedge){
            self.add_connector(cuteedge.get_start().id,
                               cuteedge.get_end().id,
                               cuteedge);
        };
        CuteEdge.destruction_callback = function(cuteedge){
            if(!confirm(_t("Deleting this transition cannot be undone.\n\nAre you sure ?"))){
                return $.Deferred().reject().promise();
            }
            return new instance.web.DataSet(self,self.connector).unlink([cuteedge.id]);
        };

    },

    // Creates a popup to edit the content of the node with id node_id
    edit_node: function(node_id){
        var self = this;
        var title = _t('Activity');
        var pop = new instance.web.form.FormOpenPopup(self);

        pop.show_element(
                self.node,
                node_id,
                self.context || self.dataset.context,
                {
                    title: _t("Open: ") + title
                }
            );

        pop.on_write.add(function() {
            self.dataset.read_index(_.keys(self.fields_view.fields)).pipe(self.on_diagram_loaded);
            });

        var form_fields = [self.parent_field];
        var form_controller = pop.view_form;

        form_controller.on_record_loaded.add_first(function() {
            _.each(form_fields, function(fld) {
                if (!(fld in form_controller.fields)) { return; }
                var field = form_controller.fields[fld];
                field.$input.prop('disabled', true);
                field.$drop_down.unbind();
                field.$menu_btn.unbind();
            });
        });
    },

    // Creates a popup to add a node to the diagram
    add_node: function(){
        var self = this;
        var title = _t('Activity');
        var pop = new instance.web.form.SelectCreatePopup(self);
        pop.select_element(
            self.node,
            {
                title: _t("Create:") + title,
                initial_view: 'form',
                disable_multiple_selection: true
            },
            self.dataset.domain,
            self.context || self.dataset.context
        );
        pop.on_select_elements.add_last(function(element_ids) {
            self.dataset.read_index(_.keys(self.fields_view.fields)).pipe(self.on_diagram_loaded);
        });

        var form_controller = pop.view_form;
        var form_fields = [this.parent_field];

        form_controller.on_record_loaded.add_last(function() {
            _.each(form_fields, function(fld) {
                if (!(fld in form_controller.fields)) { return; }
                var field = form_controller.fields[fld];
                field.set_value(self.id);
                field.dirty = true;
            });
        });
    },

    // Creates a popup to edit the connector of id connector_id
    edit_connector: function(connector_id){
        var self = this;
        var title = _t('Transition');
        var pop = new instance.web.form.FormOpenPopup(self);
        pop.show_element(
            self.connector,
            parseInt(connector_id,10),      //FIXME Isn't connector_id supposed to be an int ?
            self.context || self.dataset.context,
            {
                title: _t("Open: ") + title
            }
        );
        pop.on_write.add(function() {
            self.dataset.read_index(_.keys(self.fields_view.fields)).pipe(self.on_diagram_loaded);
        });
    },

    // Creates a popup to add a connector from node_source_id to node_dest_id.
    // dummy_cuteedge if not null, will be removed form the graph after the popup is closed.
    add_connector: function(node_source_id, node_dest_id, dummy_cuteedge){
        var self = this;
        var title = _t('Transition');
        var pop = new instance.web.form.SelectCreatePopup(self);

        pop.select_element(
            self.connector,
            {
                title: _t("Create:") + title,
                initial_view: 'form',
                disable_multiple_selection: true
            },
            this.dataset.domain,
            this.context || this.dataset.context
        );

        pop.on_select_elements.add_last(function(element_ids) {
            self.dataset.read_index(_.keys(self.fields_view.fields)).pipe(self.on_diagram_loaded);
        });
        // We want to destroy the dummy edge after a creation cancel. This destroys it even if we save the changes.
        // This is not a problem since the diagram is completely redrawn on saved changes.
        pop.$element.bind("dialogbeforeclose",function(){
            if(dummy_cuteedge){
                dummy_cuteedge.remove();
            }
        });

        var form_controller = pop.view_form;

        form_controller.on_record_loaded.add_last(function () {
            form_controller.fields[self.connectors.attrs.source].set_value(node_source_id);
            form_controller.fields[self.connectors.attrs.source].dirty = true;
            form_controller.fields[self.connectors.attrs.destination].set_value(node_dest_id);
            form_controller.fields[self.connectors.attrs.destination].dirty = true;
        });
    },

    on_pager_action: function(action) {
        switch (action) {
            case 'first':
                this.dataset.index = 0;
                break;
            case 'previous':
                this.dataset.previous();
                break;
            case 'next':
                this.dataset.next();
                break;
            case 'last':
                this.dataset.index = this.dataset.ids.length - 1;
                break;
        }
        var loaded = this.dataset.read_index(_.keys(this.fields_view.fields))
                .pipe(this.on_diagram_loaded);
        this.do_update_pager();
        return loaded;
    },

    do_update_pager: function(hide_index) {
        var $pager = this.$element.find('div.oe_diagram_pager');
        var index = hide_index ? '-' : this.dataset.index + 1;
        if(!this.dataset.count) {
            this.dataset.count = this.dataset.ids.length;
        }
        $pager.find('span.oe_pager_index').html(index);
        $pager.find('span.oe_pager_count').html(this.dataset.count);
    },

    do_show: function() {
        this.do_push_state({});
        return $.when(this._super(), this.on_pager_action('reload'));
    }
});
};

// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
