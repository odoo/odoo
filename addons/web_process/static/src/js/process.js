
openerp.web_process = function (openerp) {
var QWeb = openerp.web.qweb;
QWeb.add_template('/web_process/static/src/xml/web_process.xml');
	openerp.web.ViewManager.include({
		start: function() {
			this._super();
	        var self = this;
	        
	        this.process_check();
		},
		process_check: function() {
			var self = this,
			grandparent = this.widget_parent && this.widget_parent.widget_parent,
	        view = this.views[this.views_src[0].view_type],
	        $process_view = this.$element.find('.oe-process-view');
	        
	        this.process_model = this.model;
	        if (!(grandparent instanceof openerp.web.WebClient) ||
                !(view.view_type === this.views_src[0].view_type
                    && view.view_id === this.views_src[0].view_id)) {
	        	$process_view.hide();
                return;
            }
	        $process_view.click(function() {
        		$.when(self.load_process()).then(self.get_process_id());
	        });
		},
		
		load_process: function() {
			this.$element.html(QWeb.render("ProcessView",this));
		},
		
		get_process_id: function() {
			var self = this;
			this.process_dataset = new openerp.web.DataSetStatic(this, "process.process", this.session.context);
			this.process_dataset
				.call(
						"search_by_model",
						[self.process_model,self.session.context],
						function(res) {self.process_renderer(res)}
					);
		},
		
		process_renderer: function(res) {
			var self = this;
			if(!res.length) {
				this.process_model = false;
				this.get_process_id();
			} else {
				if(res.length > 1) {
					this.selection = res;
					$.when(this.load_process())
						.then(function(){
							var $parent = self.widget_parent.$element; 
							$parent.find('#change_process').click(function() {
								self.selection = false;
								self.p_id = $parent.find('#select_process').val();
								$.when(self.load_process()).then(self.render_process_view());
							});
						});
				} else {
					this.p_id = res[0][0];
					$.when(this.load_process()).then(this.render_process_view());
				}
			}
		},
		render_process_view: function() {
			var self = this;
			this.p_id = parseInt(this.p_id, 10);
			this.process_dataset
				.call(
					"graph_get",
					[self.p_id, self.model, false, [80,80,150,100]],
					function(res) {
						res['title'] = res.resource ? res.resource : res.name;
						self.process_dataset.call("search_by_model",[self.model,self.session.context],function(r){
							res['related'] = r;
						});
						self.draw_process_graph(res);
					}
				);
		},
		
		draw_process_graph: function(res) {
			var process_graph = new Graph();
			
			var process_renderer = function(r, n) {
				var process_node,
					process_node_text,
					process_node_desc,
					process_set;
				
	            var node_button,
	            	node_menu,
	            	img_src;
	            	
	            var bg = "node";
	            var clip_rect = "".concat(n.node.x,",",n.node.y,",150,100");
	            var text_position_x  = n.node.kind == "subflow" ? n.node.x+88 : n.node.x+75;
	            
	            //Image part
	            bg = n.node.kind == "subflow" ? "node-subflow" : "node";
	            bg = n.node.gray ? bg + "-gray" : bg;
	            img_src = '/web_process/static/src/img/'+ bg + '.png';
	            
	            r['image'](img_src, n.node.x, n.node.y,150, 100).attr({"clip-rect": clip_rect});
	            
	            //Node
	            process_node = r['rect'](n.node.x, n.node.y, 150, 100);
	            
	            // Node text
	            process_node_text =  r.text(text_position_x, n.node.y+10, (n.node.name))
	            					.attr({"fill": "#fff", "font-weight": "bold"});
	            
	            if(n.node.subflow) {
	            	process_node_text.click(function() {
	            		self.p_id = n.node.id;
	            		$.when(self.load_process()).then(self.render_process_view());
	            	});
	            }
	            
	            //Node Description
	            process_node_desc = r.text(n.node.x+75, n.node.y+50, (n.node.notes));
	            
	            
	            r['image']('/web/static/src/img/icons/gtk-info.png', n.node.x+20, n.node.y+70, 16, 16)
	            	.attr({"cursor": "pointer", "title": "Help"})
	            	.click(function(){
	            		window.open(n.node.url || "http://doc.openerp.com/v6.0/index.php?model=" + n.node.model);
	            	});
	            
	            if(n.node.menu) {
	            	r['image']('/web/static/src/img/icons/gtk-jump-to.png', n.node.x+115, n.node.y+70, 16, 16)
	            	.attr({"cursor": "pointer", "title": n.node.menu.name})
	            	.click(function() {
	            		self.jump_to_view(n.node.res_model, n.node.menu.id)
	            	});
	            }
	            
	            process_set = r.set()
	            	.push(process_node)
	            	.push(process_node_text)
	            	.push(process_node_desc);
	            process_node.mousedown(function() {
	            	return false;
	            })
	            return process_set;
			};
			
			_.each(res['nodes'],function(node, node_id) {
				node['res_model'] = self.model,
				node['res_id'] = false,
				node['id'] = node_id;
				process_graph.addNode(node['name'], {node: node,render: process_renderer});
			});
			
			_.each(res['transitions'], function(transitions) {
				
				var src = res['nodes'][transitions['source']];
				var dst = res['nodes'][transitions['target']];
				// make active
				transitions['active'] = src.active && !dst.gray;
				process_graph.addEdge(src['name'], dst['name'], {directed : true, label: transitions['name']})
			});
			var layouter = new Graph.Layout.Ordered(process_graph);
	        var render_process_graph = new Graph.Renderer.Raphael('process_canvas', process_graph, $('#process_canvas').width(), $('#process_canvas').height());
		},
		
		jump_to_view: function(model, id) {
			var self = this;
			var dataset = new openerp.web.DataSetStatic(this, 'ir.values', this.session.context);
			dataset
				.call('get',
						['action', 'tree_but_open',[['ir.ui.menu', id]], dataset.context],
						function(res) {
							var action = res[0][res[0].length - 1];
							var action_manager = new openerp.web.ActionManager(self);
							action_manager.appendTo(self.widget_parent.$element);
							action_manager.do_action(action);
						}
				);
		}
	});
};


// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
