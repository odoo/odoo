odoo.define('web_diagram.DiagramView', function (require) {
/*---------------------------------------------------------
 * OpenERP diagram library
 *---------------------------------------------------------*/
"use strict";

var core = require('web.core');
var data = require('web.data');
var form_common = require('web.form_common');
var Pager = require('web.Pager');
var View = require('web.View');
var ajax = require('web.ajax');

var _t = core._t;
var _lt = core._lt;
var QWeb = core.qweb;

var DiagramView = View.extend({
    display_name: _lt('Diagram'),
    icon: 'fa-code-fork',
    multi_record: false,
    searchable: false,

    init: function() {
        this._super.apply(this, arguments);
        this.domain = this.dataset._domain || [];
        this.context = {};
        this.ids = this.dataset.ids;
        if (this.ids && this.ids.length) {
            this.id = this.ids[this.dataset.index || 0];
        }
        this.fields = this.fields_view.fields;
        this.nodes = this.fields_view.arch.children[0];
        this.connectors = this.fields_view.arch.children[1];
        this.node = this.nodes.attrs.object;
        this.connector = this.connectors.attrs.object;
        this.labels = _.filter(this.fields_view.arch.children, function(label) {
            return label.tag === "label";
        });
    },

    willStart: function() {
        if (window.Raphael) {
            return $.when();
        }
        return $.when(
            ajax.loadJS('/web_diagram/static/lib/js/jquery.mousewheel.js'),
            ajax.loadJS('/web_diagram/static/lib/js/raphael.js')
        );
    },
    start: function() {
        var self = this;
        this.$el.html(QWeb.render("DiagramView", {'widget': this}));
        this.$el.addClass('o_diagram_view').addClass(this.fields_view.arch.attrs.class);

        _.each(this.labels,function(label){
            self.$('.o_diagram_header').append($('<span>').html(label.attrs.string));
        });

        var diagram_info;
        if(this.id) {
            diagram_info = this.get_diagram_info();
        }
        return $.when(this._super(), diagram_info);
    },

    toTitleCase: function(str) {
        return str.replace(/\w\S*/g, function(txt){return txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase();});
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
            if(child.attrs.invisible === '1')
                params.invisible_nodes.push(child.attrs.name);
            else {
                params.visible_nodes.push(child.attrs.name);
                params.node_fields.push(self.fields[child.attrs.name]['string']|| this.toTitleCase(child.attrs.name));
            }
        });

        _.each(this.connectors.children, function(conn) {
            params.connectors_fields.push(self.fields[conn.attrs.name]['string']|| this.toTitleCase(conn.attrs.name));
            params.connectors.push(conn.attrs.name);
        });
        return this.rpc(
            '/web_diagram/diagram/get_diagram_info',params).done(function(result) {
                self.draw_diagram(result);
            }
        );
    },

    on_diagram_loaded: function(record) {
        // title is displayed in breadcrumbs
        this.set({ 'title' : record.id ? record.name : _t("New") });

        var id_record = record['id'];
        if (id_record) {
            this.id = id_record;
            this.get_diagram_info();
            this.do_push_state({id: id_record});
        } else {
            this.do_push_state({});
        }
    },

    do_load_state: function(state, warm) {
        if (state && state.id) {
            if (!this.dataset.get_id_index(state.id)) {
                this.dataset.ids.push(state.id);
            }
            this.dataset.select_id(state.id);
            if (warm) {
                this.do_show();
            }
        }
     },

    // Set-up the drawing elements of the diagram
    draw_diagram: function(result) {
        var self = this;
        var res_nodes  = result['nodes'];
        var res_edges  = result['conn'];
        this.parent_field = result.parent_field;

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
        var canvas = self.$('.o_diagram').empty().get(0);

        var r  = new Raphael(canvas, '100%','100%');

        var graph  = new CuteGraph(r,style,canvas.parentNode);

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
        CuteNode.destruction_callback = function(cutenode){
            if(!confirm(_t("Deleting this node cannot be undone.\nIt will also delete all connected transitions.\n\nAre you sure ?"))){
                return $.Deferred().reject().promise();
            }
            return new data.DataSet(self,self.node).unlink([cutenode.id]);
        };
        CuteEdge.double_click_callback = function(cuteedge){
            self.edit_connector(cuteedge.id);
        };

        CuteEdge.creation_callback = function(node_start, node_end){
            return {label: ''};
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
            return new data.DataSet(self,self.connector).unlink([cuteedge.id]);
        };

    },

    // Creates a popup to edit the content of the node with id node_id
    edit_node: function(node_id){
        var self = this;
        var title = _t('Activity');
        var pop = new form_common.FormViewDialog(self, {
            res_model: self.node,
            res_id: node_id,
            context: self.context || self.dataset.context,
            title: _t("Open: ") + title
        }).open();

        pop.on('write_completed', self, function() {
            self.dataset.read_index(_.keys(self.fields_view.fields)).then(self.on_diagram_loaded);
        });
        
        pop.opened().then(function(){
            var form_controller = pop.view_form;
            var field = form_controller.fields[self.parent_field];
            if (field) {
                field.$input.prop('disabled', true);
                field.$dropdown.unbind();
            }
        });
    },

    // Creates a popup to add a node to the diagram
    add_node: function(){
        var self = this;
        var title = _t('Activity');
        var pop = new form_common.FormViewDialog(self, {
            res_model: self.node,
            domain: self.domain,
            context: self.context || self.dataset.context,
            title: _t("Create:") + title,
            disable_multiple_selection: true,
            on_selected: function(element_ids) {
                self.dataset.read_index(_.keys(self.fields_view.fields)).then(self.on_diagram_loaded);
            }
        }).open();

        pop.opened().then(function(){
            var form_controller = pop.view_form;
            var field = form_controller.fields[self.parent_field];
            if (field) {
                field.set_value(self.id);
                field.dirty = true;
            }
        });
    },

    // Creates a popup to edit the connector of id connector_id
    edit_connector: function(connector_id){
        var self = this;
        var title = _t('Transition');
        var pop = new form_common.FormViewDialog(self, {
            res_model: self.connector,
            res_id: parseInt(connector_id, 10),      //FIXME Isn't connector_id supposed to be an int ?
            context: self.context || self.dataset.context,
            title: _t("Open: ") + title
        }).open();
        pop.on('write_completed', self, function() {
            self.dataset.read_index(_.keys(self.fields_view.fields)).then(self.on_diagram_loaded);
        });
    },

    // Creates a popup to add a connector from node_source_id to node_dest_id.
    // dummy_cuteedge if not null, will be removed form the graph after the popup is closed.
    add_connector: function(node_source_id, node_dest_id, dummy_cuteedge){
        var self = this;
        var title = _t('Transition');
        var pop = new form_common.FormViewDialog(self, {
            res_model: self.connector,
            domain: this.domain,
            context: this.context || this.dataset.context,
            title: _t("Create:") + title,
            disable_multiple_selection: true,
            on_selected: function(element_ids) {
                self.dataset.read_index(_.keys(self.fields_view.fields)).then(self.on_diagram_loaded);
            }
        }).open();

        // We want to destroy the dummy edge after a creation cancel. This destroys it even if we save the changes.
        // This is not a problem since the diagram is completely redrawn on saved changes.
        pop.$el.parents('.modal').on('hidden.bs.modal', function (e){
            if(dummy_cuteedge){
                dummy_cuteedge.remove();
            }
        });

        pop.opened().then(function(){
            var form_controller = pop.view_form;
            var source_field = form_controller.fields[self.connectors.attrs.source];
            var destination_field = form_controller.fields[self.connectors.attrs.destination];
            source_field.set_value(node_source_id);
            source_field.dirty = true;
            destination_field.set_value(node_dest_id);
            destination_field.dirty = true;
        });
    },

    /**
     * Render the buttons according to the DiagramView.buttons template and add listeners on it.
     * Set this.$buttons with the produced jQuery element
     * @param {jQuery} [$node] a jQuery node where the rendered buttons should be inserted
     * $node may be undefined, in which case they are inserted into this.options.$buttons
     */
    render_buttons: function($node) {
        var self = this;

        this.$buttons = $(QWeb.render("DiagramView.buttons", {'widget': this}));
        this.$buttons.on('click', '.o_diagram_new_button', function() {
            self.add_node();
        });

        this.$buttons.appendTo($node);
    },

    /**
     * Instantiate and render the pager and add listeners on it.
     * Set this.pager
     * @param {jQuery} [$node] a jQuery node where the pager should be inserted
     * $node may be undefined, in which case the FormView inserts the pager into this.options.$pager
     */
    render_pager: function($node) {
        var self = this;

        this.pager = new Pager(this, this.dataset.ids.length, this.dataset.index + 1, 1);
        this.pager.appendTo($node || this.options.$pager);

        this.pager.on('pager_changed', this, function (new_state) {
            this.pager.disable();
            this.dataset.index = new_state.current_min - 1;
            $.when(this.reload()).then(function () {
                self.pager.enable();
            });
        });
    },
    
    update_pager: function() {
        if (this.pager) {
            this.pager.update_state({
                size: this.dataset.ids.length,
                current_min: this.dataset.index + 1,
            });
        }
    },

    reload: function() {
        return this.dataset.read_index(_.keys(this.fields_view.fields))
                .then(this.on_diagram_loaded)
                .then(this.proxy('update_pager'));
    },

    do_show: function() {
        this.do_push_state({});
        return $.when(this._super(), this.reload());
    }
});

core.view_registry.add('diagram', DiagramView);

return DiagramView;

});
