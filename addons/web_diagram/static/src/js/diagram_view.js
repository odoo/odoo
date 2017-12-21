odoo.define('web_diagram.DiagramView', function (require) {
"use strict";

var BasicView = require('web.BasicView');
var core = require('web.core');
var DiagramModel = require('web_diagram.DiagramModel');
var DiagramRenderer = require('web_diagram.DiagramRenderer');
var DiagramController = require('web_diagram.DiagramController');

var _lt = core._lt;

/**
 * Diagram View
 */
var DiagramView = BasicView.extend({
    display_name: _lt('Diagram'),
    icon: 'fa-code-fork',
    multi_record: false,
    searchable: false,
    jsLibs: [[
        '/web_diagram/static/lib/js/jquery.mousewheel.js',
        '/web_diagram/static/lib/js/raphael.js',
    ]],
    config: {
        Model: DiagramModel,
        Renderer: DiagramRenderer,
        Controller: DiagramController,
    },
    viewType: 'diagram',

    /**
     * @override
     * @param {Object} viewInfo
     * @param {Object} params
     */
    init: function (viewInfo, params) {
        this._super.apply(this, arguments);
        var self = this;
        var arch = viewInfo.arch;
        // Compute additional data for diagram model
        function toTitleCase(str) {
            return str.replace(/\w\S*/g, function (txt) {
                return txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase();
            });
        }

        var nodes = arch.children[0];
        var connectors = arch.children[1];
        var node_model = nodes.attrs.object;
        var connector_model = connectors.attrs.object;
        var labels = _.map(_.where(arch.children, {tag: 'label'}), function (label) {
            return label.attrs.string;
        });

        var invisible_nodes = [];
        var visible_nodes = [];
        var node_fields_string = [];
        _.each(nodes.children, function (child) {
            if (child.attrs.invisible === '1')
                invisible_nodes.push(child.attrs.name);
            else {
                var fieldString = self.fields[child.attrs.name].string || toTitleCase(child.attrs.name);
                visible_nodes.push(child.attrs.name);
                node_fields_string.push(fieldString);
            }
        });

        var connector_fields_string = _.map(connectors.children, function (conn) {
            return self.fields[conn.attrs.name].string || toTitleCase(conn.attrs.name);
        });

        this.loadParams = _.extend({}, this.loadParams, {
            currentId: params.currentId,
            nodes: nodes,
            labels: labels,
            invisible_nodes: invisible_nodes,
            visible_nodes: visible_nodes,
            node_fields_string: node_fields_string,
            node_model: node_model,
            connectors: connectors,
            connector_model: connector_model,
            connector_fields_string: connector_fields_string,
        });

        this.controllerParams = _.extend({}, this.controllerParams, {
            domain: params.domain,
            context: params.context,
            ids: params.ids,
            currentId: params.currentId,
        });
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * This override is quite tricky: the graph renderer uses Raphael.js to
     * render itself, so it needs it to be loaded in the window before rendering
     * However, the raphael.js library is built in such a way that if it detects
     * that a module system is present, it will try to use it.  So, in that
     * case, it is not available on window.Raphael.  This means that the diagram
     * view is then broken.
     *
     * As a workaround, we simply remove and restore the define function, if
     * present, while we are loading Raphael.
     *
     * @override
     */
    getController: function () {
        var oldDefine = window.define;
        delete window.define;
        return this._super.apply(this, arguments).then(function (view) {
            window.define = oldDefine;
            return view;
        });
    },
});

return DiagramView;

});
