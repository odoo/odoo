/*---------------------------------------------------------
 * OpenERP diagram library
 *---------------------------------------------------------*/

openerp.web_diagram = function (openerp) {
var QWeb = openerp.web.qweb,
      _t = openerp.web._t,
     _lt = openerp.web._lt;
openerp.web.views.add('diagram', 'openerp.web.DiagramView');
openerp.web.DiagramView = openerp.web.View.extend({
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

    on_diagram_loaded: function(record) {
        var id_record = record['id'];
        if(id_record) {
            this.id = id_record;
            this.get_diagram_info();
        }
    },
    select_node: function (node, element) {
        if (!this.selected_node) {
            this.selected_node = node;
            element.attr('stroke', 'red');
            return;
        }
        // Re-click selected node, deselect it
        if (node.id === this.selected_node.id) {
            this.selected_node = null;
            element.attr('stroke', 'black');
            return;
        }
        this.add_edit_node(null, this.connector, {
            act_from: this.selected_node.id,
            act_to: node.id
        });
    },
    draw_diagram: function(result) {
        this.selected_node = null;
        var diagram = new Graph();

        this.active_model = result['id_model'];

        var res_nodes = result['nodes'];
        var res_connectors = result['conn'];
        this.parent_field = result.parent_field;

        //Custom logic
        var self = this;
        var renderer = function(r, n) {
            var shape = (n.node.shape === 'rectangle') ? 'rect' : 'ellipse';

            var node = r[shape](n.node.x, n.node.y).attr({
                "fill": n.node.color
            });

            var nodes = r.set(node, r.text(n.node.x, n.node.y, (n.label || n.id)))
                .attr("cursor", "pointer")
                .dblclick(function() {
                    self.add_edit_node(n.node.id, self.node);
                })
                .mousedown(function () { node.moved = false; })
                .mousemove(function () { node.moved = true; })
                .click(function () {
                    // Ignore click from move event
                    if (node.moved) { return; }
                    self.select_node(n.node, node);
                });

            if (shape === 'rect') {
                node.attr({width: "60", height: "44"});
                node.next.attr({"text-anchor": "middle", x: n.node.x + 20, y: n.node.y + 20});
            } else {
                node.attr({rx: "40", ry: "20"});
            }

            return nodes;
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

        self.$element.find('.diagram').empty();

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

    add_edit_node: function(id, model, defaults) {
        defaults = defaults || {};
        var self = this;

        if(!model)
            model = self.node;
        if(id)
            id = parseInt(id, 10);
        
        var pop,
            title = model == self.node ? _t('Activity') : _t('Transition');
        if(!id) {
            pop = new openerp.web.form.SelectCreatePopup(this);
            pop.select_element(
                model,
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
        } else {
            pop = new openerp.web.form.FormOpenPopup(this);
            pop.show_element(
                model,
                id,
                this.context || this.dataset.context,
                {
                    title: _t("Open: ") + title
                }
            );
            pop.on_write.add(function() {
                self.dataset.read_index(_.keys(self.fields_view.fields)).pipe(self.on_diagram_loaded);
            });
        }

        var form_controller = pop.view_form;

        var form_fields;

        if (model === self.node) {
            form_fields = [this.parent_field];
            if (!id) {
                form_controller.on_record_loaded.add_last(function() {
                    _.each(form_fields, function(fld) {
                        if (!(fld in form_controller.fields)) { return; }
                        var field = form_controller.fields[fld];
                        field.set_value([self.id,self.active_model]);
                        field.dirty = true;
                    });
                });
            } else {
                form_controller.on_record_loaded.add_first(function() {
                    _.each(form_fields, function(fld) {
                        if (!(fld in form_controller.fields)) { return; }
                        var field = form_controller.fields[fld];
                        field.$input.prop('disabled', true);
                        field.$drop_down.unbind();
                        field.$menu_btn.unbind();
                    });
                });
            }
        } else {
            form_fields = [
                this.connectors.attrs.source,
                this.connectors.attrs.destination];
        }

        if (!_.isEmpty(defaults)) {
            form_controller.on_record_loaded.add_last(function () {
                _(form_fields).each(function (field) {
                    if (!defaults[field]) { return; }
                    form_controller.fields[field].set_value(defaults[field]);
                    form_controller.fields[field].dirty = true;
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
        this.dataset.read_index(_.keys(this.fields_view.fields)).pipe(this.on_diagram_loaded);
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

    do_show: function() {
        this.do_push_state({});
        return this._super();
    }
});
};

// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
