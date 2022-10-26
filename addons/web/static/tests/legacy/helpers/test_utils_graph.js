odoo.define('web.test_utils_graph', function () {
"use strict";

/**
 * Graph Test Utils
 *
 * This module defines various utility functions to help test graph views.
 *
 * Note that all methods defined in this module are exported in the main
 * testUtils file.
 */


/**
 * Reloads a graph view.
 *
 * @param {GraphController} graph
 * @param {[Object]} params given to the controller reload method
 */
function reload(graph, params) {
    return graph.reload(params);
}

return {
    reload: reload,
};

});
