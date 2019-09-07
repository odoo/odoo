odoo.define('web_diagram.DiagramModel', function (require) {
"use strict";

var AbstractModel = require('web.AbstractModel');

/**
 * DiagramModel
 */
var DiagramModel = AbstractModel.extend({
    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     * @returns {Object}
     */
    get: function () {
        return $.extend(true, {}, {
            labels: this.labels,
            nodes: this.datanodes,
            edges: this.edges,
            node_model: this.node_model,
            parent_field: this.parent_field,
            res_id: this.res_id,
            connector_model: this.connector_model,
            connectors: this.connectors,
        });
    },
    /**
     * @override
     * @param {Object} params
     * @returns {Promise}
     */
    load: function (params) {
        this.modelName = params.modelName;
        this.res_id = params.res_id;
        this.node_model = params.node_model;
        this.connector_model = params.connector_model;
        this.connectors = params.connectors;
        this.nodes = params.nodes;
        this.visible_nodes = params.visible_nodes;
        this.invisible_nodes = params.invisible_nodes;
        this.node_fields_string = params.node_fields_string;
        this.connector_fields_string = params.connector_fields_string;
        this.labels = params.labels;

        return this._fetchDiagramInfo();
    },
    reload: function () {
        return this._fetchDiagramInfo();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {any} record
     * @returns {Promise}
     */
    _fetchDiagramInfo: function () {
        var self = this;
        return this._rpc({
                route: '/web_diagram/diagram/get_diagram_info',
                params: {
                    id: this.res_id,
                    model: this.modelName,
                    node: this.node_model,
                    connector: this.connector_model,
                    src_node: this.connectors.attrs.source,
                    des_node: this.connectors.attrs.destination,
                    label: this.connectors.attrs.label || false,
                    bgcolor: this.nodes.attrs.bgcolor,
                    shape: this.nodes.attrs.shape,
                    visible_nodes: this.visible_nodes,
                    invisible_nodes: this.invisible_nodes,
                    node_fields_string: this.node_fields_string,
                    connector_fields_string: this.connector_fields_string,
                },
            })
            .then(function (data) {
                self.datanodes = data.nodes;
                self.edges = data.conn;
                self.parent_field = data.parent_field;
            });
    },
});

return DiagramModel;
});
