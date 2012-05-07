/*---------------------------------------------------------
 * OpenERP web_graph
 *---------------------------------------------------------*/

openerp.web_graph = function (instance) {

var QWeb = instance.web.qweb,
     _lt = instance.web._lt;

instance.web.views.add('graph', 'instance.web_graph.GraphView');
instance.web_graph.GraphView = instance.web.View.extend({
    display_name: _lt('Graph'),
    view_type: "graph",

    init: function(parent, dataset, view_id, options) {
        this._super(parent);
        this.set_default_options(options);
        this.dataset = dataset;
        this.view_id = view_id;

        this.mode="pie";          // line, bar, area, pie, radar
        this.orientation=true;    // true: horizontal, false: vertical
        this.stacked=true;
        this.spreadsheet=false;   // Display data gris, allows copy to CSV
        this.forcehtml=false;
        this.legend_container;
        this.legend="top";        // top, inside, no


        this.is_loaded = $.Deferred();
        this.renderer = null;
    },
    destroy: function () {
        if (this.renderer) {
            clearTimeout(this.renderer);
        }
        this._super();
    },



    on_loaded: function(fields_view_get) {
        var self = this;
        self.fields_view = fields_view_get;
        return this.dataset.call_and_eval('fields_get', [false, {}], null, 1).pipe(function(fields_result) {
            self.fields = fields_result;
            return self.on_loaded_2();
        });
    },
    /**
     * Returns all object fields involved in the graph view
     */
    list_fields: function () {
        var fs = [this.abscissa];
        fs.push.apply(fs, _(this.columns).pluck('name'));
        if (this.group_field) {
            fs.push(this.group_field);
        }
        return fs;
    },
    on_loaded_2: function() {
        this.chart = this.fields_view.arch.attrs.type || 'pie';
        this.orientation = this.fields_view.arch.attrs.orientation || 'vertical';

        _.each(this.fields_view.arch.children, function (field) {
            var attrs = field.attrs;
            if (attrs.group) {
                this.group_field = attrs.name;
            } else if(!this.abscissa) {
                this.first_field = this.abscissa = attrs.name;
            } else {
                this.columns.push({
                    name: attrs.name,
                    operator: attrs.operator || '+'
                });
            }
        }, this);
        this.ordinate = this.columns[0].name;
        this.is_loaded.resolve();
        return $.when();
    },

    schedule_chart: function(results) {
        var self = this;
        this.$element.html(QWeb.render("GraphView", {
            "fields_view": this.fields_view,
            "chart": this.chart,
            'element_id': this.getParent().element_id
        }));

        var fields = _(this.columns).pluck('name').concat([this.abscissa]);
        if (this.group_field) { fields.push(this.group_field); }

    },
    do_search: function(domain, context, group_by) {
        var self = this;
        return $.when(this.is_loaded).pipe(function() {
            // TODO: handle non-empty group_by with read_group?
            if (!_(group_by).isEmpty()) {
                self.abscissa = group_by[0];
            } else {
                self.abscissa = self.first_field;
            }
            return self.dataset.read_slice(self.list_fields()).then($.proxy(self, 'schedule_chart'));
        });
    },

    do_show: function() {
        this.do_push_state({});
        return this._super();
    },

});
};
