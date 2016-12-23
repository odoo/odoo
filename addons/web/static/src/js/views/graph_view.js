odoo.define('web.GraphView', function (require) {
"use strict";
/*---------------------------------------------------------
 * Odoo Graph view
 *---------------------------------------------------------*/

var core = require('web.core');
var data_manager = require('web.data_manager');
var GraphWidget = require('web.GraphWidget');
var View = require('web.View');

var _lt = core._lt;
var _t = core._t;
var QWeb = core.qweb;

var GraphView = View.extend({
    className: 'o_graph',
    display_name: _lt('Graph'),
    icon: 'fa-bar-chart',
    require_fields: true,

    init: function () {
        this._super.apply(this, arguments);

        this.measures = [];
        this.active_measure = '__count__';
        this.initial_groupbys = [];
        this.widget = undefined;
    },
    willStart: function () {
        var self = this;
        var fields_def = data_manager.load_fields(this.dataset).then(this.prepare_fields.bind(this));
        this.fields_view.arch.children.forEach(function (field) {
            var name = field.attrs.name;
            if (field.attrs.interval) {
                name += ':' + field.attrs.interval;
            }
            if (field.attrs.type === 'measure') {
                self.active_measure = name;
            } else {
                self.initial_groupbys.push(name);
            }
        });
        return $.when(this._super(), fields_def);
    },
    /**
     * Render the buttons according to the GraphView.buttons and
     * add listeners on it.
     * Set this.$buttons with the produced jQuery element
     * @param {jQuery} [$node] a jQuery node where the rendered buttons should be inserted
     * $node may be undefined, in which case the GraphView does nothing
     */
    render_buttons: function ($node) {
        if ($node) {
            var context = {measures: _.pairs(_.omit(this.measures, '__count__'))};
            this.$buttons = $(QWeb.render('GraphView.buttons', context));
            this.$measure_list = this.$buttons.find('.o_graph_measures_list');
            this.update_measure();
            this.$buttons.find('button').tooltip();
            this.$buttons.click(this.on_button_click.bind(this));

            this.$buttons.find('.o_graph_button[data-mode="' + this.widget.mode + '"]').addClass('active');

            this.$buttons.appendTo($node);  
        }
    },
    update_measure: function () {
        var self = this;
        this.$measure_list.find('li').each(function (index, li) {
            $(li).toggleClass('selected', $(li).data('field') === self.active_measure);
        });
    },
    do_show: function () {
        this.do_push_state({});
        return this._super();
    },
    prepare_fields: function (fields) {
        var self = this;
        this.fields = fields;
        _.each(fields, function (field, name) {
            if ((name !== 'id') && (field.store === true)) {
                if (field.type === 'integer' || field.type === 'float' || field.type === 'monetary') {
                    self.measures[name] = field;
                }
            }
        });
        this.measures.__count__ = {string: _t("Count"), type: "integer"};
    },
    do_search: function (domain, context, group_by) {
        if (!this.widget) {
            this.initial_groupbys = context.graph_groupbys || (group_by.length ? group_by : this.initial_groupbys);
            this.widget = new GraphWidget(this, this.model, {
                measure: context.graph_measure || this.active_measure,
                mode: context.graph_mode || this.active_mode,
                domain: domain,
                groupbys: this.initial_groupbys,
                context: context,
                fields: this.fields,
                stacked: this.fields_view.arch.attrs.stacked !== "False" 
            });
            // append widget
            this.widget.appendTo(this.$el);
        } else {
            var groupbys = group_by.length ? group_by : this.initial_groupbys.slice(0);
            this.widget.update_data(domain, groupbys);
        }
    },
    get_context: function () {
        return !this.widget ? {} : {
            graph_mode: this.widget.mode,
            graph_measure: this.widget.measure,
            graph_groupbys: this.widget.groupbys
        };
    },
    on_button_click: function (event) {
        var $target = $(event.target);
        if ($target.hasClass('o_graph_button')) {
            this.widget.set_mode($target.data('mode'));
            this.$buttons.find('.o_graph_button.active').removeClass('active');
            $target.addClass('active');
        }
        else if ($target.parents('.o_graph_measures_list').length) {
            var parent = $target.parent();
            var field = parent.data('field');
            this.active_measure = field;
            event.preventDefault();
            event.stopPropagation();
            this.update_measure();
            this.widget.set_measure(this.active_measure);
        }
    },
    destroy: function () {
        if (this.$buttons) {
            this.$buttons.find('button').off(); // remove jquery's tooltip() handlers
        }
        return this._super.apply(this, arguments);
    },
});

core.view_registry.add('graph', GraphView);

return GraphView;

});
