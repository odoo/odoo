openerp.process = function (instance) {
var QWeb = instance.web.qweb,
      _t = instance.web._t;
instance.web.ViewManager.include({
    start: function() {
        var self = this;
        var _super = this._super();
        this.process_help = this.action ? this.action.help : '';
        if(this.action) {
            this.process_model = this.action.res_model;
        } else {
            this.process_model = this.dataset.model;
        }
        this.$el.on('click', '.oe_process', function(ev) { self.initialize_process_view(ev);});
        return _super;
    },
    initialize_process_view: function(ev) {
        var self = this;
        this.record_id = false;
        if(this.active_view == 'form') {
            this.record_id = this.views[this.active_view].controller.datarecord.id;
        }
        this.process_get_object().then(function(process) {
            if(process && process.length) {
                if(process.length > 1) {
                    self.process_selection = process;
                } else {
                    self.process_id = process[0][0],
                    self.process_title = process[0][1];
                }
            }
            return $.Deferred().resolve();
        }).then(function() {
            var def = $.Deferred();
            if(self.process_id) {
                $.when(self.process_graph_get()).done(function(res) {
                    self.process_notes = res.notes;
                    self.process_title = res.name;
                    self.process_subflows = _(res.nodes).chain()
                          .filter(function (node) { return node['subflow'] !== false; })
                          .uniq(false, function (node) { return node['subflow'][0]; }).value();
                    self.process_related = res.related;
                    def.resolve(res);
                });
            } else def.resolve();
            return def.promise();
        }).done(function(res) {
            $.when(self.process_render_view()).done(function() {
                if(res) {
                    self.process_draw_graph(res);
                }
            });
        });
    },
    process_graph_get: function() {
        var self = this;
        var def = $.Deferred();
        this.process_id = parseInt(this.process_id, 10);
        this.process_dataset
        .call("graph_get",[self.process_id, self.model || self.dataset.model, self.record_id, [80,80,150,100], self.session.user_context])
        .done(function(res) {
            self.process_dataset
                .call("search_by_model",[self.model || self.dataset.model, self.session.user_context])
                .done(
                function(r) {
                    res['related'] = r;
                    def.resolve(res);
                });
        });
        return def.promise();
    },
    process_get_object : function() {
        var self = this,
            def = $.Deferred();
        if(this.process_id)
            return def.resolve().promise();
        this.process_dataset = new instance.web.DataSet(self, "process.process", self.session.user_context);
        this.process_dataset
        .call("search_by_model", [self.process_model,self.session.user_context])
        .done(function(res) {
            if (!res.length) {
                self.process_model = false;
                self.process_get_object().done(def.resolve);
            }
            else {
                def.resolve(res);
            }
        })
        .fail(def.reject);
        return def.promise();
    },
    process_render_view : function() {
        var self = this;
        this.$el.html(QWeb.render("process.ProcessView", this));
        this.$el.addClass('oe_view_process').css({'background-color':'#F0EEEE'});
        this.$el.find('#edit_process').click(function() {
            self.process_edit_view();
        });
        var $parent = this.getParent().$el;
        $parent.find('#change_process').click(function() {
            self.process_selection = false,
            self.process_id = $parent.find('#select_process').val(),
            self.process_title = $.trim($parent.find('#select_process option:selected').text());
            self.initialize_process_view();
        });
        this.$el.find(".process_subflow").click(function() {
            self.process_id = this.id;
            self.initialize_process_view();
        });
    },
    process_draw_graph : function(result) {
        var self = this;
        var res_nodes = result['nodes'];
        var res_edges = result['transitions'];
        var id_to_node = {};
        var canvas = $('div.process_canvas').empty().get(0);
        var style = {
            edge_color: "#A0A0A0",
            edge_label_font_size: 10,
            edge_width: 2,
            edge_spacing: 40,
            edge_loop_radius: 200,

            node_label_color: "#333",
            node_label_font_size: 12,
            node_outline_color: "#333",
            node_outline_width: 1,
            node_outline_color: "#F5F5F5",
            node_outline_width: 0,
            node_selected_width: 0,
            node_size_x: 150,
            node_size_y: 100,

            gray: "#DCDCDC",
            white: "#FFF",
            viewport_margin: 50
        };
        var r  = new Raphael(canvas,'100%','100%');
        var graph  = new CuteGraph(r,style,canvas.parentNode);
        var render_process = function(r,nodes){
            //For Image 
            var image_node = nodes.kind == "subflow" ? "node-subflow" : "node";
            image_node = nodes.gray ? image_node + "-gray" : image_node;
            image_node = nodes.active ? 'node-current': image_node;
            var img_src = '/process/static/src/img/'+ image_node + '.png';
            var image = r['image'](img_src, nodes.x-25, nodes.y,150, 100).attr({"cursor": "default"}) .mousedown(function() { return false; });
            //For Node
            var process_node = r['rect'](nodes.x, nodes.y, 150, 150).attr({stroke: "none"});
            // Node text
            if(nodes.name.length > 18){
               var text = nodes.name.substr(0,16) + '...'
            }
            var node_text =  r.text(nodes.x+60, nodes.y+10,(text || nodes.name.substr(0,18))).attr({"fill": "#fff","font-weight": "bold", "cursor": "default","title":nodes.name});
            //Node Description
            var new_notes = nodes.notes;
            if(nodes.notes.length > 25) {
               var to;
               var temp_str = new_notes = '';
               var from = to = 0;
               while (1) {
                 from = 25;
                 temp_str = nodes.notes.substr(to, 25);
                 if (temp_str.lastIndexOf(" ") < 25 && temp_str.length >= 25) {
                      from = temp_str.lastIndexOf(" ");
                 }
                 new_notes += "\n" + nodes.notes.substr(to, from);
                 if (new_notes.length > 80){
                     break;
                 }
                 to += from;
              }
            }
            if(nodes.res)
                 new_notes = nodes.res.name + '\n' + new_notes;
            if(nodes.notes.length > 60){
                var notes = new_notes.substring(0,60) +'..';
            }
            r.text(nodes.x+60, nodes.y+30, (notes || new_notes)).attr({"title":nodes.notes,"cursor": "default"});
            r['image']('/web/static/src/img/icons/gtk-info.png', nodes.x, nodes.y+75, 16, 16)
              .attr({"cursor": "pointer", "title": "Help"})
              .click(function() {
                   window.open(nodes.url || "http://doc.openerp.com/v6.1/index.php?model=" + nodes.model);
              });
            if(nodes.menu) {
                 r['image']('/web/static/src/img/icons/gtk-jump-to.png', nodes.x+100, nodes.y+75, 16, 16)
                    .attr({"cursor": "pointer", "title": nodes.menu.name})
                    .click(function() {
                        self.process_jump_to_view(nodes.res_model, nodes.menu.id);
                 });
            }
            var process_set =r.set().push(process_node);
            process_set.mousedown(function() {
                    return false;
            });
            return process_set;
        }
        _.each(res_nodes, function(node,id) {
            node['res_model'] = self.model,
            node['res_id'] = false,
            node['color'] = 'gray'
            var n = new CuteNode(
                graph,
                node.x + 50,  //FIXME the +50 should be in the layout algorithm
                node.y + 50,
                CuteGraph.wordwrap("", 14));
            n.id = id;
            id_to_node[id] = n;
            return render_process(r,node);
        });
        _.each(res_edges, function(edge) {
            var e =  new CuteEdge(
                graph,
                CuteGraph.wordwrap(" ",0),
                id_to_node[edge.source],
                id_to_node[edge.target] || id_to_node[edge.source]);
            e.id = edge.id;
        });
    },
    process_jump_to_view: function(model,id) {
        var self = this;
        var dataset = new instance.web.DataSet(this, 'ir.values', this.session.user_context);
        var action_manager = new instance.web.ActionManager(self);
        dataset.call('get',
            ['action', 'tree_but_open',[['ir.ui.menu', id]], dataset.context]).done(function(res) {
                var action = res[0][res[0].length - 1];
                self.rpc("/web/action/load", {
                    action_id: action.id,
                    context: dataset.context
                    }).done(function(result) {
                        action_manager.replace(self.$el);
                        action_manager.do_action(result);
                    })
            });
    },
    process_edit_view: function() {
        var self = this;
        var pop = new instance.web.form.FormOpenPopup(self);
        pop.show_element(
            self.process_dataset.model,
            self.process_id,
            self.context || self.dataset.context,
            {
                title: _t('Process')
            });
        var form_controller = pop.view_form;
        pop.on('write_completed', self, self.initialize_process_view);
    }
});
};
// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
