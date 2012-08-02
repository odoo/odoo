openerp.web_process = function (instance) {
    var QWeb = instance.web.qweb,
          _t = instance.web._t;
    instance.web.ViewManager.include({
        start: function() {
            var _super = this._super();
            this.process_check();
            this.process_help = this.action ? this.action.help : 'Help: Not Defined';
            this.model = this.dataset.model;
            if(this.action) this.process_model = this.action.res_model;
            else this.process_model = this.model;
            return _super;
        },
        process_check: function() {
            var self = this,
            grandparent = this.getParent() && this.getParent().getParent(),
            view = this.views[this.views_src[0].view_type],
            $process_view = this.$element.find('.oe_process');
            if (!(grandparent instanceof instance.web.WebClient) ||
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
            this.record_id = false;
            if(this.active_view == 'form') {
                this.record_id = this.views[this.active_view].controller.datarecord.id;
            }

            $.when(this.help(), this.get_process_object()).pipe(function(help, process) {
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
            .call("graph_get",[this.process_id, this.model || this.dataset.model, this.record_id, [80,80,150,100]])
            .done(function(res) {
                self.process_dataset
                    .call("search_by_model",[self.model || self.dataset.model,self.session.context])
                    .done(
                    function(r) {
                        res['related'] = r;
                        def.resolve(res);
                    });
            });
            return def.promise();
        },
        help : function() {
            var def = $.Deferred();
            if(!this.subflow_model) {
                def.resolve(this.action ? (this.action.help!=false ? this.action.help : 'Help: Not Defined') : 'Help: Not Defined');
            } else {
                 var dataset = new instance.web.DataSetSearch(this, "ir.actions.act_window", this.session.context, []);
                 dataset
                    .read_slice(['help'],
                    {
                        domain: [
                            ['res_model', '=', this.subflow_model],
                            ['name', 'ilike', this.subflow_name]
                        ]
                    }
                    ).done(function(res) {
                        def.resolve(res.help || 'Help: Not Defined');
                    });
            }
            return def.promise();
        },
        get_process_object : function() {
            var self = this,
                def = $.Deferred();
            if(this.process_id)
                return def.resolve().promise();

            this.process_dataset = new instance.web.DataSet(this, "process.process", this.session.context);
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
            var $parent = this.getParent().$element;
            $parent.find('#change_process').click(function() {
                self.process_selection = false,
                self.process_id = $parent.find('#select_process').val(),
                self.process_title = $.trim($parent.find('#select_process option:selected').text());
                self.initialize_process_view();
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
                var clip_rect = "".concat(n.node.x,",",n.node.y,",150,100");

                //Image part
                var bg = n.node.kind == "subflow" ? "node-subflow" : "node";
                bg = n.node.gray ? bg + "-gray" : bg;
                bg = n.node.active ? 'node-current': bg;

                var img_src = '/web_process/static/src/img/'+ bg + '.png';

                r['image'](img_src, n.node.x, n.node.y,150, 100)
                    .attr({"clip-rect": clip_rect})
                    .mousedown(function() {
                        return false;
                });
                //Node
                var process_node = r['rect'](n.node.x, n.node.y, 150, 100).attr({stroke: "none"});
                // Node text
                var process_node_text =  r.text(n.node.x, n.node.y, (n.node.name))
                    .attr({"fill": "#fff", "font-weight": "bold", "cursor": "pointer"});
                process_node_text.translate((process_node.getBBox().width / 2) + 5, 10);
                if(n.node.subflow) {
                    process_node_text.click(function() {
                        self.process_id = n.node.subflow[0];
                        self.subflow_model = n.node.model;
                        self.subflow_name = n.node.name;
                        self.initialize_process_view();
                    });
                }
                //Node Description
                var new_notes = n.node.notes;
                if(n.node.notes.length > 25) {
                    var to;
                    var temp_str = new_notes = '';
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

                if(n.node.res)
                    new_notes = n.node.res.name + '\n' + new_notes;

                r.text(n.node.x+85, n.node.y+50, (new_notes));
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

                var process_set = r.set().push(process_node);
                process_set.mousedown(function() {
                    return false;
                });
                return process_set;
            };

            _.each(res['nodes'],function(node, node_id) {
                node['res_model'] = self.model,
                node['res_id'] = false,
                node['id'] = node_id;
                process_graph.addNode(node.id, {node: node,render: process_renderer});
            });

            _.each(res['transitions'], function(transitions) {
                var src = res['nodes'][transitions['source']];
                var dst = res['nodes'][transitions['target']];
                // make active
                transitions['active'] = src.active && !dst.gray;
                process_graph.addEdge(src.id, dst.id, {directed : true});
            });
            var width = $(document).width();
            var height = $(document).height();
            var layouter = new Graph.Layout.Ordered(process_graph);
            var render_process_graph = new Graph.Renderer.Raphael('process_canvas', process_graph, width, height);
        },
        jump_to_view: function(model, id) {
            var self = this;
            var dataset = new instance.web.DataSet(this, 'ir.values', this.session.context);
            dataset.call('get',
                ['action', 'tree_but_open',[['ir.ui.menu', id]], dataset.context],
                function(res) {
                    var action = res[0][res[0].length - 1];
                    self.rpc("/web/action/load", {
                        action_id: action.id,
                        context: dataset.context
                        }, function(result) {
                            var action_manager = new instance.web.ActionManager(self);
                            action_manager.replace(self.$element);
                            action_manager.do_action(result.result);
                        });
                });
        },
        edit_process_view: function() {
            var self = this;
            var action_manager = new instance.web.ActionManager(this);
            var dialog = new instance.web.Dialog(this, {
                width: 800,
                buttons : [
                    {text: _t("Cancel"), click: function() { $(this).dialog('destroy'); }},
                    {text: _t("Save"), click: function() {
                        var form_view = action_manager.inner_widget.views.form.controller;

                        form_view.do_save(function() {
                            self.initialize_process_view();
                        });
                        $(this).dialog('destroy');
                    }}
                ]
            }).open();

            action_manager.appendTo(dialog.$element);
            action_manager.do_action({
                res_model : 'process.process',
                res_id: self.process_id,
                views : [[false, 'form']],
                type : 'ir.actions.act_window',
                flags : {
                    search_view: false,
                    sidebar : false,
                    views_switcher : false,
                    action_buttons : false,
                    pager: false
                }
            });
        }
    });
};
// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
