/*---------------------------------------------------------
 * OpenERP base library
 *---------------------------------------------------------*/

openerp.base_diagram = function (openerp) {
QWeb.add_template('/base_diagram/static/src/xml/base_diagram.xml');
openerp.base.views.add('diagram', 'openerp.base_diagram.DiagramView');
openerp.base_diagram.DiagramView = openerp.base.View.extend({
	init: function(parent, element_id, dataset, view_id, options) {
		this._super(parent, element_id);
		this.set_default_options(options);
        this.view_manager = parent;
        this.dataset = dataset;
        this.model = this.dataset.model;
        this.view_id = view_id;
        this.name = "";
		this.domain = this.dataset._domain ? this.dataset._domain: [];
		this.context = {};
		this.ids = this.dataset.ids;
	},
	start: function() {
		return this.rpc("/base_diagram/diagram/load", {"model": this.model, "view_id": this.view_id}, this.on_loaded);
	},
	
	toTitleCase: function(str) {
		return str.replace(/\w\S*/g, function(txt){return txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase();});
	},
	
	on_loaded: function(result) {
		
		var self = this;
		if(this.ids && this.ids.length) {
			this.id = this.ids[self.dataset.index || 0];
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
		
		this.$element.html(QWeb.render("DiagramView", this));
		
		this.$element.find('div.oe_diagram_pager button[data-pager-action]').click(function() {
            var action = $(this).data('pager-action');
            self.on_pager_action(action);
        });
		
		this.do_update_pager();
		
		this.$element.find('.oe_diagram_button_new').click(function(){self.add_edit_node()})
		
        if(this.id) {
        	self.get_diagram_info();
        }
	},
	
	get_diagram_info: function() {
		var self = this;
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
        );
	},
	
	on_diagram_loaded: function(record) {
    	var self = this;
    	var id_record = record['id']
    	if(id_record) {
        	self.get_diagram_info();
        }
    },
    
    draw_diagram: function(result) {
        var dia = new Graph();
        
        this.active_model = result['id_model'];
        this.in_transition_field = result['in_transition_field'];
        this.out_transition_field = result['out_transition_field'];
        var res_nodes = result['nodes'];
        var res_connectors = result['conn'];
        
        //Custom logic
        var self = this;
        var renderer= function(r, n) {
	        var node;
	        var set;
        
	        // ellipse
	        if (n.node.shape == 'ellipse') {
	            var node = r.ellipse(n.node.x - 30, n.node.y - 13, 40, 20).attr({
	                    "fill": n.node.color,
	                    r: "12px",
	                    "stroke-width": n.distance == 0 ? "3px" : "1px"
	                });
	            
	            set = r.set().push(node).push(r.text(n.node.x - 30, n.node.y - 10, (n.label || n.id)));
	        }
        
	        // rectangle
			else if(n.node.shape == 'rectangle') {
				var node = r.rect(n.node.x-30, n.node.y-13, 60, 44).attr({
	             	"fill": n.node.color, 
	                 r : "12px", 
	                "stroke-width" : n.distance == 0 ? "3px" : "1px" 
	                });
	        	set = r.set().push(node).push(r.text(n.node.x , n.node.y+5 , (n.label || n.id)));
			}
        
	        // circle
			else {
	            var node = r.circle(n.node.x, n.node.y, 150).attr({
	                        "fill": n.node.color, 
	                        r : "30px", 
	                        "stroke-width" : n.distance == 0 ? "3px" : "1px" 
	                });
	           	set = r.set().push(node).push(r.text(n.node.x , n.node.y , (n.label || n.id)));
			}
	        
	        //Shape Node Event
	        jQuery(node.node).attr({
	            'id': n.node.id,
	            'name': n.id,
	            'kind': n.node.options['Kind'] || n.node.options['kind']
	        }).dblclick(function() {
	            var $this = jQuery(this);
	            self.add_edit_node($this.attr('id'), self.node);
//	            self.search_activity($this.attr('id'), $this.attr('name'), $this.attr('kind'))
	        });
	        
	        //Text Node Event
	        jQuery(node.next.node).attr({
	            'id': n.node.id,
	            'name': n.id,
	            'kind': n.node.options['Kind'] || n.node.options['kind']
	        }).dblclick(function() {
	            var $this = jQuery(this);
	            self.add_edit_node($this.attr('id'), self.node);
//	            self.search_activity($this.attr('id'), $this.attr('name'), $this.attr('kind'))
	        });
	        return set;
        }
        
        for(node in res_nodes) {
            var res_node = res_nodes[node];
            dia.addNode(res_node['name'],{node: res_node,render: renderer});
        }
        
        for(cr in res_connectors) {
        	var res_connector = res_connectors[cr];
        	dia.addEdge(res_connector['source'], res_connector['destination'], {directed : true});
        }
        
        var layouter = new Graph.Layout.Spring(dia);
        layouter.layout();
        if ($('div#dia-canvas').children().length > 0) {
        	$('div#dia-canvas').children().remove();
        }
        var renderer = new Graph.Renderer.Raphael('dia-canvas', dia, $('div#dia-canvas').width(), $('div#dia-canvas').height());
        renderer.draw();
        
        //Path(Edges)
        jQuery('path',renderer.r.canvas).each(function(index, path) {
        	
        	$(this).attr({
        		'd_id': res_connectors[index+1].d_id,
        		'id': res_connectors[index+1].id,
        		's_id': res_connectors[index+1].s_id,
    		})
        });
        jQuery('path',renderer.r.canvas).dblclick(function() {
        	self.add_edit_node(this.id, self.connector)
        });
    },
    
    add_edit_node: function(id, model) {
    	var self = this;
    	
    	if(!model)
    		model = self.node;
    	if(id)
    		id = parseInt(id, 10);
    	var action_manager = new openerp.base.ActionManager(this);
    	var dialog = new openerp.base.Dialog(this, {
            width: 800,
            height: 600,
            buttons : {
                Cancel : function() {
                    $(this).dialog('destroy');
                },
                Save : function() {
                	var form_dataset = action_manager.inner_viewmanager.dataset; 
                	var form_view = action_manager.inner_viewmanager.views.form.controller;
                	
                	form_view.do_save(function() {
                		self.dataset.index = jQuery.inArray(parseInt(self.id,10), self.dataset.ids)
                		self.dataset.read_index(_.keys(self.fields_view.fields), self.on_diagram_loaded)
                	});
                    $(this).dialog('destroy');
                }
            }
        }).start().open();
    	action_manager.appendTo(dialog.$element);
    	action_manager.do_action({
            res_model : model,
            res_id: id,
            views : [[false, 'form']],
            type : 'ir.actions.act_window',
            auto_search : false,
            flags : {
    			search_view: false,
                sidebar : false,
                views_switcher : false,
                action_buttons : false
            }
        });
    },
    
    do_search: function(domains, contexts, groupbys) {
        var self = this;
        this.rpc('/base/session/eval_domain_and_context', {
            domains: domains,
            contexts: contexts,
            group_by_seq: groupbys
        }, function (results) {
            // TODO: handle non-empty results.group_by with read_group
            self.dataset.context = self.context = results.context;
            self.dataset.domain = self.domain = results.domain;
            self.dataset.read_slice(self.fields, 0, self.limit,function(events){
                self.schedule_events(events)
            });
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
	    this.dataset.read_index(_.keys(this.fields_view.fields), this.on_diagram_loaded);
	    this.do_update_pager();
    },
    
    do_update_pager: function(hide_index) {
        var $pager = this.$element.find('div.oe_diagram_pager');
        var index = hide_index ? '-' : this.dataset.index + 1;
        if(!this.dataset.count)
        	this.dataset.count = this.dataset.ids.length
        $pager.find('span.oe_pager_index').html(index);
        $pager.find('span.oe_pager_count').html(this.dataset.count);
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
