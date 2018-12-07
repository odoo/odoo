odoo.define('web.GraphModel', function (require) {
"use strict";

/**
 * The graph model is responsible for fetching and processing data from the
 * server.  It basically just do a read_group and format/normalize data.
 */

var AbstractModel = require('web.AbstractModel');

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
     * @param {Object} params.intervalMapping object linking fieldNames with intervals.
     *   this could be useful to simplify the code. For now this parameter is not used.
     * @returns {Deferred} The deferred does not return a handle, we don't need
     *   to keep track of various entities.
     */
    load: function (params) {
        var groupBys = params.context.graph_groupbys || params.groupBys;
        this.initialGroupBys = groupBys;
        this.fields = params.fields;
        this.modelName = params.modelName;
        this.chart = {
            compare: params.compare,
            comparisonTimeRange: params.comparisonTimeRange,
            data: [],
            groupedBy: params.groupedBy.length ? params.groupedBy : groupBys,
            // this parameter is not used anywhere for now.
            // the idea would be to seperate intervals from
            // fieldnames in groupbys. This could be done
            // in graph view only or everywhere but this is
            // a big refactoring.
            intervalMapping: params.intervalMapping,
            measure: params.context.graph_measure || params.measure,
            mode: params.context.graph_mode || params.mode,
            timeRange: params.timeRange,
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
            var timeRangeMenuData = params.context.timeRangeMenuData;
            if (timeRangeMenuData) {
                this.chart.timeRange = timeRangeMenuData.timeRange || [];
                this.chart.comparisonTimeRange = timeRangeMenuData.comparisonTimeRange || [];
                this.chart.compare = this.chart.comparisonTimeRange.length > 0;
            } else {
                this.chart.timeRange = [];
                this.chart.comparisonTimeRange = [];
                this.chart.compare = false;
                this.chart = _.omit(this.chart, 'comparisonData');
            }
        }
        if ('domain' in params) {
            this.chart.domain = params.domain;
        }
        if ('groupBy' in params) {
            this.chart.groupedBy = params.groupBy.length ? params.groupBy : this.initialGroupBys;
        }
        if ('intervalMapping' in params) {
            this.chart.intervalMapping = params.intervalMapping;
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
            if (this.fields[this.chart.measure].type === 'many2one') {
                fields = fields.concat(this.chart.measure + ":count_distinct");
            }
            else {
                fields = fields.concat(this.chart.measure);
            }
        }

        var context = _.extend({fill_temporal: true}, this.chart.context);
        var defs = [];
        defs.push(this._rpc({
            model: this.modelName,
            method: 'read_group',
            context: context,
            domain: this.chart.domain.concat(this.chart.timeRange),
            fields: fields,
            groupBy: groupedBy,
            lazy: false,
        }).then(this._processData.bind(this, 'data')));

        if (this.chart.compare) {
            defs.push(this._rpc({
                model: this.modelName,
                method: 'read_group',
                context: context,
                domain: this.chart.domain.concat(this.chart.comparisonTimeRange),
                fields: fields,
                groupBy: groupedBy,
                lazy: false,
            }).then(this._processData.bind(this, 'comparisonData')));
        }

        return $.when.apply($, defs);
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
     * @param {String} dataKey
     * @param {any} raw_data result from the read_group
     */
    _processData: function (dataKey, raw_data) {
        var self = this;
        var is_count = this.chart.measure === '__count__';
        var data_pt, labels;

        this.chart[dataKey] = [];
        for (var i = 0; i < raw_data.length; i++) {
            data_pt = raw_data[i];
            labels = _.map(this.chart.groupedBy, function (field) {
                return self._sanitizeValue(data_pt[field], field);
            });
            var count = data_pt.__count || data_pt[this.chart.groupedBy[0]+'_count'] || 0;
            var value = is_count ? count : data_pt[this.chart.measure];
            if (value instanceof Array) {
                // when a many2one field is used as a measure AND as a grouped
                // field, bad things happen.  The server will only return the
                // grouped value and will not aggregate it.  Since there is a
                // nameclash, we are then in the situation where this value is
                // an array.  Fortunately, if we group by a field, then we can
                // say for certain that the group contains exactly one distinct
                // value for that field.
                value = 1;
            }
            this.chart[dataKey].push({
                count: count,
                value: value,
                labels: labels,
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
        var fieldName = field.split(':')[0];
        if (value === false && this.fields[fieldName].type !== 'boolean') {
            return undefined;
        }
        if (value instanceof Array) return value[1];
        if (field && (this.fields[fieldName].type === 'selection')) {
            var selected = _.where(this.fields[fieldName].selection, {0: value})[0];
            return selected ? selected[1] : value;
        }
        return value;
    },
});

});
