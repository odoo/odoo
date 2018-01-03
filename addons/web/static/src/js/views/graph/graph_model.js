odoo.define('web.GraphModel', function (require) {
"use strict";

/**
 * The graph model is responsible for fetching and processing data from the
 * server.  It basically just do a read_group and format/normalize data.
 */

var core = require('web.core');
var AbstractModel = require('web.AbstractModel');

var _t = core._t;

return AbstractModel.extend({
    /**
     * @override
     * @param {Widget} parent
     */
    init: function () {
        this._super.apply(this, arguments);
        this.chart = null;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * We defend against outside modifications by extending the chart data. It
     * may be overkill.
     *
     * @todo Adding the fields parameter looks wrong.  If the renderer or the
     * controller need the fields, they should get it via their init method.
     *
     * @returns {Object}
     */
    get: function () {
        return _.extend({}, this.chart, {
            fields: this.fields
        });
    },
    /**
     * Initial loading.
     *
     * @todo All the work to fall back on the graph_groupbys keys in the context
     * should be done by the graphView I think.
     *
     * @param {Object} params
     * @param {string} params.mode one of 'pie', 'bar', 'line
     * @param {string} params.measure a valid field name
     * @param {string[]} params.groupBys a list of valid field names
     * @param {Object} params.context
     * @param {string[]} params.domain
     * @returns {Deferred} The deferred does not return a handle, we don't need
     *   to keep track of various entities.
     */
    load: function (params) {
        var groupBys = params.context.graph_groupbys || params.groupBys;
        this.initialGroupBys = groupBys;
        this.fields = params.fields;
        this.modelName = params.modelName;
        this.chart = {
            data: [],
            groupedBy: params.groupedBy.length ? params.groupedBy : groupBys,
            measure: params.context.graph_measure || params.measure,
            mode: params.context.graph_mode || params.mode,
            domain: params.domain,
            context: params.context,
        };
        return this._loadGraph();
    },
    /**
     * Reload data.  It is similar to the load function. Note that we ignore the
     * handle parameter, we always expect our data to be in this.chart object.
     *
     * @todo This method takes 'groupBy' and load method takes 'groupedBy'. This
     *   is insane.
     *
     * @param {any} handle ignored!
     * @param {Object} params
     * @param {string[]} [params.domain]
     * @param {string[]} [params.groupBy]
     * @param {string} [params.mode] one of 'bar', 'pie', 'line'
     * @param {string} [params.measure] a valid field name
     * @returns {Deferred}
     */
    reload: function (handle, params) {
        if ('context' in params) {
            this.chart.context = params.context;
            this.chart.groupedBy = params.context.graph_groupbys || this.chart.groupedBy;
            this.chart.measure = params.context.graph_measure || this.chart.measure;
            this.chart.mode = params.context.graph_mode || this.chart.mode;
        }
        if ('domain' in params) {
            this.chart.domain = params.domain;
        }
        if ('groupBy' in params) {
            this.chart.groupedBy = params.groupBy.length ? params.groupBy : this.initialGroupBys;
        }
        if ('measure' in params) {
            this.chart.measure = params.measure;
        }
        if ('mode' in params) {
            this.chart.mode = params.mode;
            return $.when();
        }
        return this._loadGraph();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Fetch and process graph data.  It is basically a read_group with correct
     * fields.  We have to do some light processing to separate date groups
     * in the field list, because they can be defined with an aggregation
     * function, such as my_date:week
     *
     * @returns {Deferred}
     */
    _loadGraph: function () {
        var groupedBy = this.chart.groupedBy;
        var fields = _.map(groupedBy, function (groupBy) {
            return groupBy.split(':')[0];
        });
        if (this.chart.measure !== '__count__') {
            fields = fields.concat(this.chart.measure);
        }
        return this._rpc({
                model: this.modelName,
                method: 'read_group',
                context: this.chart.context,
                domain: this.chart.domain,
                fields: fields,
                groupBy: groupedBy,
                lazy: false,
            })
            .then(this._processData.bind(this));
    },
    /**
     * Since read_group is insane and returns its result on different keys
     * depending of some input, we have to normalize the result.
     * The final chart data is added to this.chart object.
     *
     * @todo This is not good for race conditions.  The processing should get
     *  the object this.chart in argument, or an array or something. We want to
     *  avoid writing on a this.chart object modified by a subsequent read_group
     *
     * @param {any} raw_data result from the read_group
     */
    _processData: function (raw_data) {
        var self = this;
        var is_count = this.chart.measure === '__count__';
        var data_pt, labels;

        this.chart.data = [];
        for (var i = 0; i < raw_data.length; i++) {
            data_pt = raw_data[i];
            labels = _.map(this.chart.groupedBy, function (field) {
                return self._sanitizeValue(data_pt[field], field);
            });
            this.chart.data.push({
                value: is_count ? data_pt.__count || data_pt[this.chart.groupedBy[0]+'_count'] : data_pt[this.chart.measure],
                labels: labels
            });
        }
    },
    /**
     * Helper function (for _processData), turns various values in a usable
     * string form, that we can display in the interface.
     *
     * @param {any} value some value received by the read_group rpc
     * @param {string} field the name of the corresponding field
     * @returns {string}
     */
    _sanitizeValue: function (value, field) {
        if (value === false) return _t("Undefined");
        if (value instanceof Array) return value[1];
        if (field && this.fields[field] && (this.fields[field].type === 'selection')) {
            var selected = _.where(this.fields[field].selection, {0: value})[0];
            return selected ? selected[1] : value;
        }
        return value;
    },
});

});
