/*---------------------------------------------------------
 * OpenERP base library
 *---------------------------------------------------------*/

openerp.base.diagram = function (openerp) {
	
openerp.base.views.add('diagram', 'openerp.base.DiagramView');
openerp.base.DiagramView = openerp.base.Controller.extend({
	init: function(view_manager, session, element_id, dataset, view_id){
		this._super(session, element_id);
        this.view_manager = view_manager;
        this.dataset = dataset;
        this.model = dataset.model;
        this.view_id = view_id;
        this.name = "";
		this.domain = this.dataset._domain ? this.dataset._domain: [];
		this.context = {};
		this.ids = this.dataset.ids;
		
		console.log('data set>>',this.dataset)
	},
	start: function() {
		this.rpc("/base_diagram/diagram/load", {"model": this.model, "view_id": this.view_id}, this.on_loaded);
	},
	
	toTitleCase: function(str) {
		return str.replace(/\w\S*/g, function(txt){return txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase();});
	},
	
	on_loaded: function(result) {
		
		var self = this;
		if(this.ids && this.ids.length) {
			this.id = this.ids[0];
		}
		
		this.fields_view = result.fields_view;
		this.view_id = this.fields_view.view_id;
		this.name = this.fields_view.name;
		
		this.fields = this.fields_view.fields;
		
		var children = this.fields_view.arch.children;
		/*
		 * For Nodes (Fields)
		 */
		this.node = '';
		this.bgcolor = '';
		this.shape = '';
		this.visible_fields_nodes = [];
		this.invisible_fields_nodes = [];
		this.fields_nodes_string = [];
		
		/*
		 * For Arraows(Connector)
		 */
		this.connector = '';
		this.src_node = '';
		this.des_node = '';
		this.connector_fields = [];
		this.fields_connector_string = [];
		
		for(ch in children) {
			if(children[ch]['tag'] == 'node') {
				this.node = children[ch]['attrs']['object'];
				this.bgcolor = children[ch]['attrs']['bgcolor'] || '';
				this.shape = children[ch]['attrs']['shape'] || '';
				for(node_chld in children[ch]['children']) {
					if (children[ch]['children'][node_chld]['tag'] = 'field') {
						var ch_name = children[ch]['children'][node_chld]['attrs']['name'];
						
						if (children[ch]['children'][node_chld]['attrs']['invisible']) {
							if (children[ch]['children'][node_chld]['attrs']['invisible'] == 1 && children[ch]['children'][node_chld]['attrs']['invisible'] == '1') {
								this.invisible_fields_nodes.push(ch_name)
							}
						}
						else {
							this.visible_fields_nodes.push(ch_name);
							var ch_node_string = this.fields[ch_name]['string'] || this.toTitleCase(ch_name);
							this.fields_nodes_string.push(ch_node_string)
						}
					}
				}
			} else if(children[ch]['tag'] == 'arrow') {
				this.connector = children[ch]['attrs']['object'];
				this.src_node = children[ch]['attrs']['source'];
				this.des_node = children[ch]['attrs']['destination'];
				for (arrow_chld in children[ch]['children']) {
					if (children[ch]['children'][arrow_chld]['tag'] = 'field') {
						var arr_ch_name = children[ch]['children'][arrow_chld]['attrs']['name'];
						var ch_node_string = this.fields[arr_ch_name]['string'] || this.toTitleCase(arr_ch_name);
						this.fields_connector_string.push(ch_node_string);
						this.connector_fields.push(arr_ch_name);
					}
				}
			}
		}
		this.$element.html(QWeb.render("DiagramView", {"fields_view": this.fields_view}));
		
 
//		g.addEdge("strawberry", "cherry");
//		g.addEdge("strawberry", "apple");
//		g.addEdge("strawberry", "tomato");
//		 
//		g.addEdge("tomato", "apple");
//		g.addEdge("tomato", "kiwi");
//		 
//		g.addEdge("cherry", "apple");
//		g.addEdge("cherry", "kiwi");
		 
		
		
		if(this.id) {
			this.rpc(
			'/base_diagram/diagram/get_diagram_info',
			{
				'id': this.id,
				'model': this.model,
				'bgcolor': this.bgcolor,
				'shape': this.shape,
				'node': this.node,
				'connector': this.connector,
				'src_node': this.src_node,
				'des_node': this.des_node,
				'visible_node_fields': this.visible_fields_nodes,
				'invisible_node_fields': this.invisible_fields_nodes,
				'node_fields_string': this.fields_nodes_string,
				'connector_fields': this.connector_fields,
				'connector_fields_string': this.fields_connector_string
			},
			function(result) {
				self.draw_diagram(result);
			}
			)
		}
	},
	
	draw_diagram: function(result) {
		console.log('this>>>',this)
		var g = new Graph();
		
		this.in_transition_field = result['in_transition_field'];
		this.out_transition_field = result['out_transition_field'];
		var res_nodes = result['nodes'];
		var res_connectors = result['conn'];
//		for(nd in res_nodes) {
//			var res_node = res_nodes[nd];
//			console.log('nodes',res_node, res_node['shape'])
//			var state;
//		}
		
		for(cr in res_connectors) {
			var res_connector = res_connectors[cr];
			g.addEdge(res_connector['source'], res_connector['destination']);
			
		}
		
		var layouter = new Graph.Layout.Spring(g);
		layouter.layout();
		
		var renderer = new Graph.Renderer.Raphael('dia-canvas', g, 800, 500);
		renderer.draw();
	},
	
	do_show: function () {
        this.$element.show();
    },
	
    do_hide: function () {
        this.$element.hide();
    }
});
};

// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
