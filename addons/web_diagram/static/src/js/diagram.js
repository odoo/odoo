/*---------------------------------------------------------
 * OpenERP diagram library
 *---------------------------------------------------------*/

openerp.web_diagram = function (openerp) {
var QWeb = openerp.web.qweb;
QWeb.add_template('/web_diagram/static/src/xml/base_diagram.xml');
openerp.web.views.add('diagram', 'openerp.web.DiagramView');
openerp.web.DiagramView = openerp.web.View.extend({
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
        this._super();
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

        this.$element.find('div.oe_diagram_pager button[data-pager-action]').click(function() {
            var action = $(this).data('pager-action');
            self.on_pager_action(action);
        });

        this.do_update_pager();

        // New Node,Edge
        this.$element.find('#new_node.oe_diagram_button_new').click(function(){self.add_edit_node(null, self.node);});
        this.$element.find('#new_edge.oe_diagram_button_new').click(function(){self.add_edit_node(null, self.connector);});

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

    on_diagram_loaded: function(record) {
        var id_record = record['id'];
        if(id_record) {
            this.id = id_record;
            this.get_diagram_info();
        }
    },

    draw_diagram: function(result) {
        var diagram = new Graph();

        this.active_model = result['id_model'];

        var res_nodes = result['nodes'];
        var res_connectors = result['conn'];

        //Custom logic
        var self = this;
        var renderer = function(r, n) {
            var node;
            var set;
            var shape = n.node.shape;
            if(shape == 'rectangle')
                shape = 'rect';
            node = r[shape](n.node.x, n.node.y).attr({
                "fill": n.node.color
            }).dblclick(function() {
                self.add_edit_node(n.node.id, self.node);
            });
            set = r.set()
                    .push(node)
                    .push(
                        r.text(n.node.x, n.node.y, (n.label || n.id))
                        .attr({"cursor":"pointer"})
                        .dblclick(function() {
                            self.add_edit_node(n.node.id, self.node);
                        })
                    );
            node.attr({cursor: "pointer"});

            if(shape == "ellipse")
                node.attr({rx: "40", ry: "20"});
            else if(shape == 'rect') {
                node.attr({width: "60", height: "44"});
                node.next.attr({"text-anchor": "middle", x: n.node.x + 20, y: n.node.y + 20});
            }
            return set;
        };

        _.each(res_nodes, function(res_node) {
            diagram.addNode(res_node['name'],{node: res_node,render: renderer});
        });

        // Id for Path(Edges)
        var edge_ids = [];

        _.each(res_connectors, function(connector, index) {
            edge_ids.push(index);
            diagram.addEdge(connector['source'], connector['destination'], {directed : true, label: connector['signal']});
        });


        if ($('div#dia-canvas').children().length > 0) {
            $('div#dia-canvas').children().remove();
        }

        var layouter = new Graph.Layout.Ordered(diagram);
        var render_diagram = new Graph.Renderer.Raphael('dia-canvas', diagram, $('div#dia-canvas').width(), $('div#dia-canvas').height());

        _.each(diagram.edges, function(edge, index) {
            if(edge.connection) {
                edge.connection.fg.attr({cursor: "pointer"}).dblclick(function() {
                    self.add_edit_node(edge_ids[index], self.connector);
                });
            }
        });
    },

    add_edit_node: function(id, model) {
        var self = this;

        if(!model)
            model = self.node;
        if(id)
            id = parseInt(id, 10);
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
                        self.dataset.read_index(_.keys(self.fields_view.fields), self.on_diagram_loaded);
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
                action_buttons : false,
                pager: false
            }
        });

        var form_controller = action_manager.inner_viewmanager.views.form.controller;

        var form_fields;

        if(model == self.node) {
            form_fields = ['wkf_id'];
        } else {
            form_fields = ['act_from', 'act_to'];
        }

        if(model == self.node || id) {
            $.each(form_fields, function(index, fld) {
                form_controller.on_record_loaded.add_first(function() {
                    form_controller.fields[fld].modifiers.readonly = true;
                    form_controller.fields[fld].$input.attr('disabled', true);
                    form_controller.fields[fld].$drop_down.unbind();
                    form_controller.fields[fld].$menu_btn.unbind();
                });
            });
        }
        if(!id && (model == self.node)) {
            $.each(form_fields, function(index, fld) {
                form_controller.on_record_loaded.add_last(function() {
                    form_controller.fields[fld].set_value([self.id,self.active_model]);
                    form_controller.fields[fld].dirty = true;
                });
            });
        }
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
        if(!this.dataset.count) {
            this.dataset.count = this.dataset.ids.length;
        }
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
