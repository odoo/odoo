/*---------------------------------------------------------
 * OpenERP web_graph
 *---------------------------------------------------------*/

openerp.web_graph = function (instance) {

var _lt = instance.web._lt;
var _t = instance.web._t;


instance.web.views.add('graph', 'instance.web_graph.GraphView');
instance.web_graph.GraphView = instance.web.View.extend({
    template: "GraphView",
    display_name: _lt('Graph'),
    view_type: "graph",

    init: function(parent, dataset, view_id, options) {
        this._super(parent, dataset, view_id, options);
    },

    do_show: function () {
        this.do_push_state({});
        return this._super();
    },


});
};
