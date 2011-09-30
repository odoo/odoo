openerp.web_process = function (openerp) {
    var QWeb = openerp.web.qweb;
    QWeb.add_template('/web_process/static/src/xml/web_process.xml');
    openerp.web.ViewManager.include({
        start: function() {
            this._super();
            var self = this;
            this.process_check();
            this.process_help = this.action ? this.action.help : 'Help: Not Defined';
            this.process_model = this.model;
        },
        process_check: function() {
            var self = this,
            grandparent = this.widget_parent && this.widget_parent.widget_parent,
            view = this.views[this.views_src[0].view_type],
            $process_view = this.$element.find('.oe-process-view');
            
            if (!(grandparent instanceof openerp.web.WebClient) ||
                !(view.view_type === this.views_src[0].view_type
                    && view.view_id === this.views_src[0].view_id)) {
                        $process_view.hide();
                        return;
            }
            
            $process_view.click(function() {
                self.initialize_process_view();
            });
            
        },
        
        initialize_process_view: function() {
            var self = this;
            $.when(this.fields_get(), this.help(), this.get_process_object()).pipe(function(fields, help, process) {
                self.process_fields = fields;
                self.process_help = help;
                if(process && process.length) {
                    if(process.length > 1) {
                        self.process_selection = process;
                    } else {
                        self.process_id = process[0][0],
                        self.process_title = process[0][1];
                    }
                }
                return $.Deferred().resolve();
            }).pipe(function() {
                var def = $.Deferred();
                if(self.process_id) {
                    self.graph_get().done(function(res) {
                        self.process_notes = res.notes;
                        self.process_subflows = _.filter(res.nodes, function(x) {
                            return x.subflow != false;
                        });
                        self.process_related = res.related;
                        def.resolve(res);
                    });
                } else def.resolve();
                return def.promise();
            }).done(function(res) {
                $.when(self.render_process_view()).done(function() {
                    if(res) self.draw_process_graph(res);
                });
            });
        },
        
        graph_get: function() {
            var self = this;
            var def = $.Deferred();
            this.process_id = parseInt(this.process_id, 10);
            
            this.process_dataset
            .call("graph_get",[this.process_id, this.model, false, [80,80,150,100]])
            .done(function(res) {
                self.process_dataset
                    .call("search_by_model",[self.model,self.session.context])
                    .done(
                    function(r) {
                        res['related'] = r;
                        def.resolve(res);
                    });
                
            });
            return def.promise();
        },
        
        fields_get : function() {
            var self = this,
                def = $.Deferred(),
                dataset = new openerp.web.DataSetStatic(this, this.model, this.session.context);
            
            dataset
                .call('fields_get',[])
                .done(function(fields) {
                    def.resolve(fields);
                }).fail(def.reject);
            return def.promise();
        },
        
        help : function() {
            var self = this,
                def = $.Deferred();
            if(!this.subflow_model) {
                def.resolve(this.action ? this.action.help : 'Help: Not Defined');
            } else {
                 var dataset = new openerp.web.DataSetSearch(this, "ir.actions.act_window", this.session.context, []);
                 dataset
                    .read_slice(['help'],
                    {
                        domain: [
                            ['res_model', '=', this.subflow_model], 
                            ['name', 'ilike', this.subflow_name]
                        ]
                    }
                    ).done(function(res) {
                        def.resolve(res && res.records.length ? res.records[0].help : 'Help: Not Defined');
                    });
                 
            }
            return def.promise();
        },
        
        get_process_object : function() {
            var self = this,
                def = $.Deferred();
            if(this.process_id)
                return def.resolve().promise();
            this.process_dataset = new openerp.web.DataSetStatic(this, "process.process", this.session.context);
            this.process_dataset
            .call("search_by_model", [self.process_model,self.session.context])
            .done(function(res) {
                if (!res.length) {
                    self.process_model = false;
                    self.get_process_object().done(def.resolve);
                }
                else {
                    def.resolve(res);
                }
            })
            .fail(def.reject);
            return def.promise();
        },
        
        render_process_view : function() {
            this.$element.html(QWeb.render("ProcessView", this));
            var self = this;
            this.$element.find('#edit_process').click(function() {
                self.edit_process_view();
            });
            
            var $parent = this.widget_parent.$element;
            $parent.find('#change_process').click(function() {
                self.process_selection = false,
                self.process_id = $parent.find('#select_process').val(),
                self.process_title = $.trim($parent.find('#select_process option:selected').text());
                self.initialize_process_view();
            });
            
            this.$element.find(".toggle_fields").click(function() {
                $(this).children().toggle();
                self.$element.find('.process_fields').toggle();
            });
            
            this.$element.find(".process_subflow").click(function() {
                self.process_id = this.id;
                self.initialize_process_view();
            });
        },
        
        draw_process_graph : function(res) {
            var self = this,
                process_graph = new Graph();
            
            var process_renderer = function(r, n) {
                var process_node,
                    process_node_text,
                    process_node_desc,
                    process_set;

                var node_button,
                    node_menu,
                    img_src;

                var bg = "node",
                    clip_rect = "".concat(n.node.x,",",n.node.y,",150,100");

                //Image part
                bg = n.node.kind == "subflow" ? "node-subflow" : "node";
                bg = n.node.gray ? bg + "-gray" : bg;
                img_src = '/web_process/static/src/img/'+ bg + '.png';

                r['image'](img_src, n.node.x, n.node.y,150, 100)
                    .attr({"clip-rect": clip_rect})
                    .mousedown(function() {
                        return false;
                });

                //Node
                process_node = r['rect'](n.node.x, n.node.y, 150, 100).attr({stroke: "none"});
                // Node text
                process_node_text =  r.text(n.node.x, n.node.y, (n.node.name))
                    .attr({"fill": "#fff", "font-weight": "bold", "cursor": "pointer"});
                process_node_text.translate((process_node.getBBox().width/ 2) + 5, 10)
                if(n.node.subflow) {
                    process_node_text.click(function() {
                        self.process_id = n.node.subflow[0];
                        self.subflow_model = n.node.model;
                        self.subflow_name = n.node.name;
                        self.initialize_process_view();
                    });
                }

                //Node Description
                new_notes = n.node.notes;
                if(n.node.notes.length > 25) {
                    var new_notes= temp_str = '';
                    var from = to = 0;
                    while (1) {
                        from = 25;
                        temp_str = n.node.notes.substr(to ,25);
                        if (temp_str.lastIndexOf(" ") < 25 && temp_str.length >= 25) {
                            from  =  temp_str.lastIndexOf(" ");
                        }
                        new_notes += "\n" + n.node.notes.substr(to , from);
                        if(new_notes.length > n.node.notes.length) break;
                        to += from;
                    }
                }
                process_node_desc = r.text(n.node.x+85, n.node.y+50, (new_notes));
                r['image']('/web/static/src/img/icons/gtk-info.png', n.node.x+20, n.node.y+70, 16, 16)
                    .attr({"cursor": "pointer", "title": "Help"})
                    .click(function() {
                        window.open(n.node.url || "http://doc.openerp.com/v6.0/index.php?model=" + n.node.model);
                    });

                if(n.node.menu) {
                    r['image']('/web/static/src/img/icons/gtk-jump-to.png', n.node.x+115, n.node.y+70, 16, 16)
                    .attr({"cursor": "pointer", "title": n.node.menu.name})
                    .click(function() {
                        self.jump_to_view(n.node.res_model, n.node.menu.id);
                    });
                }

                process_set = r.set().push(process_node);
                process_set.mousedown(function() {
                    return false;
                });
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
                process_graph.addEdge(src['name'], dst['name'], {directed : true});
            });

            var layouter = new Graph.Layout.Ordered(process_graph);
            var render_process_graph = new Graph.Renderer.Raphael('process_canvas', process_graph, $('#process_canvas').width(), $('#process_canvas').height());
        },
        
        jump_to_view: function(model, id) {
            var self = this;
            var dataset = new openerp.web.DataSetStatic(this, 'ir.values', this.session.context);
            dataset.call('get',
                ['action', 'tree_but_open',[['ir.ui.menu', id]], dataset.context],
                function(res) {
                    self.$element.empty();
                    var action = res[0][res[0].length - 1];
                    self.rpc("/web/action/load", {
                        action_id: action.id,
                        context: dataset.context
                        }, function(result) {
                            var action_manager = new openerp.web.ActionManager(self);
                            action_manager.appendTo(self.widget_parent.$element);
                            action_manager.do_action(result.result);
                        });
                });
        },
        
        edit_process_view: function() {
            var self = this;
            var action_manager = new openerp.web.ActionManager(this);
            var dialog = new openerp.web.Dialog(this, {
                width: 800,
                height: 600,
                buttons : {
                    Cancel : function() {
                        $(this).dialog('destroy');
                    },
                    Save : function() {
                        var form_view = action_manager.inner_viewmanager.views.form.controller;
    
                        form_view.do_save(function() {
                            self.initialize_process_view();
                        });
                        $(this).dialog('destroy');
                    }
                }
            }).start().open();
            
            action_manager.appendTo(dialog.$element);
            action_manager.do_action({
                res_model : 'process.process',
                res_id: self.process_id,
                views : [[false, 'form']],
                type : 'ir.actions.act_window',
                auto_search : false,
                flags : {
                    search_view: false,
                    sidebar : false,
                    views_switcher : false,
                    action_buttons : false,
                    pager: false
                }
            });
        },
    });
};


// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
