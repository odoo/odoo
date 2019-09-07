odoo.define('web.GraphModel', function (require) {
"use strict";

var core = require('web.core');
var _t = core._t;

/**
 * The graph model is responsible for fetching and processing data from the
 * server.  It basically just do a(some) read_group(s) and format/normalize data.
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
     *
     * We defend against outside modifications by extending the chart data. It
     * may be overkill.
     *
     * @override
     * @returns {Object}
     */
    get: function () {
        var self = this;
        return _.extend({}, this.chart, {
            comparisonFieldIndex: self._getComparisonFieldIndex(),
        });
    },
    /**
     * Initial loading.
     *
     * @todo All the work to fall back on the graph_groupbys keys in the context
     * should be done by the graphView I think.
     *
     * @param {Object} params
     * @param {boolean} params.compare
     * @param {Object} params.context
     * @param {Object} params.fields
     * @param {string[]} params.comparisonTimeRange
     * @param {string[]} params.domain
     * @param {string[]} params.groupBys a list of valid field names
     * @param {string[]} params.groupedBy a list of valid field names
     * @param {boolean} params.stacked
     * @param {string[]} params.timeRange
     * @param {string} params.comparisonField
     * @param {string} params.comparisonTimeRangeDescription
     * @param {string} params.measure a valid field name
     * @param {'pie'|'bar'|'line'} params.mode
     * @param {string} params.modelName
     * @param {string} params.timeRangeDescription
     * @returns {Promise} The promise does not return a handle, we don't need
     *   to keep track of various entities.
     */
    load: function (params) {
        var groupBys = params.context.graph_groupbys || params.groupBys;
        this.initialGroupBys = groupBys;
        this.fields = params.fields;
        this.modelName = params.modelName;
        this.chart = {
            comparisonField: params.comparisonField,
            comparisonTimeRange: params.comparisonTimeRange,
            comparisonTimeRangeDescription: params.comparisonTimeRangeDescription,
            compare: params.compare,
            context: params.context,
            dataPoints: [],
            domain: params.domain,
            groupBy: params.groupedBy.length ? params.groupedBy : groupBys,
            measure: params.context.graph_measure || params.measure,
            mode: params.context.graph_mode || params.mode,
            origins: [],
            stacked: params.stacked,
            timeRange: params.timeRange,
            timeRangeDescription: params.timeRangeDescription,
        };
        return this._loadGraph(this._getDomains());
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
     * @param {boolean} [params.stacked]
     * @param {Object} [params.context]
     * @param {string[]} [params.domain]
     * @param {string[]} [params.groupBy]
     * @param {string} [params.measure] a valid field name
     * @param {string} [params.mode] one of 'bar', 'pie', 'line'
     * @returns {Promise}
     */
    reload: function (handle, params) {
        if ('context' in params) {
            this.chart.context = params.context;
            this.chart.groupBy = params.context.graph_groupbys || this.chart.groupBy;
            this.chart.measure = params.context.graph_measure || this.chart.measure;
            this.chart.mode = params.context.graph_mode || this.chart.mode;
            var timeRangeMenuData = params.context.timeRangeMenuData;
            if (timeRangeMenuData) {
                this.chart.comparisonField = timeRangeMenuData.comparisonField || undefined;
                this.chart.comparisonTimeRange = timeRangeMenuData.comparisonTimeRange || [];
                this.chart.compare = this.chart.comparisonTimeRange.length > 0;
                this.chart.comparisonTimeRangeDescription = timeRangeMenuData.comparisonTimeRangeDescription;
                this.chart.timeRange = timeRangeMenuData.timeRange || [];
                this.chart.timeRangeDescription = timeRangeMenuData.timeRangeDescription;
            } else {
                this.chart.comparisonField = undefined;
                this.chart.comparisonTimeRange = [];
                this.chart.compare = false;
                this.chart.comparisonTimeRangeDescription = undefined;
                this.chart.timeRange = [];
                this.chart.timeRangeDescription = undefined;
            }
        }
        if ('domain' in params) {
            this.chart.domain = params.domain;
        }
        if ('groupBy' in params) {
            this.chart.groupBy = params.groupBy.length ? params.groupBy : this.initialGroupBys;
        }
        if ('measure' in params) {
            this.chart.measure = params.measure;
        }
        if ('mode' in params) {
            this.chart.mode = params.mode;
            return Promise.resolve();
        }
        if ('stacked' in params) {
            this.chart.stacked = params.stacked;
            return Promise.resolve();
        }
        return this._loadGraph(this._getDomains());
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @returns {number}
     */
    _getComparisonFieldIndex: function () {
        var groupBys = this.chart.groupBy.map(function (gb) {
            return gb.split(":")[0];
        });
        return groupBys.indexOf(this.chart.comparisonField);
    },
    /**
     * @private
     * @returns {Array[]}
     */
    _getDomains: function () {
        var domains = [this.chart.domain.concat(this.chart.timeRange)];
        this.chart.origins = [this.chart.timeRangeDescription || ""];
        if (this.chart.compare) {
            domains.push(this.chart.domain.concat(this.chart.comparisonTimeRange));
            this.chart.origins.push(this.chart.comparisonTimeRangeDescription);
        }
        return domains;
    },
    /**
     * Fetch and process graph data.  It is basically a(some) read_group(s)
     * with correct fields for each domain.  We have to do some light processing
     * to separate date groups in the field list, because they can be defined
     * with an aggregation function, such as my_date:week.
     *
     * @private
     * @param {Array[]} domains
     * @returns {Promise}
     */
    _loadGraph: function (domains) {
        var self = this;
        this.chart.dataPoints = [];
        var groupBy = this.chart.groupBy;
        var fields = _.map(groupBy, function (groupBy) {
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

        domains.forEach(function (domain, originIndex) {
            defs.push(self._rpc({
                model: self.modelName,
                method: 'read_group',
                context: context,
                domain: domain,
                fields: fields,
                groupBy: groupBy,
                lazy: false,
            }).then(self._processData.bind(self, originIndex)));
        });
        return Promise.all(defs);
    },
    /**
     * Since read_group is insane and returns its result on different keys
     * depending of some input, we have to normalize the result.
     * Each group coming from the read_group produces a dataPoint
     *
     * @todo This is not good for race conditions.  The processing should get
     *  the object this.chart in argument, or an array or something. We want to
     *  avoid writing on a this.chart object modified by a subsequent read_group
     *
     * @private
     * @param {number} originIndex
     * @param {any} rawData result from the read_group
     */
    _processData: function (originIndex, rawData) {
        var self = this;
        var isCount = this.chart.measure === '__count__';
        var labels;

        function getLabels (dataPt) {
            return self.chart.groupBy.map(function (field) {
                return self._sanitizeValue(dataPt[field], field.split(":")[0]);
            });
        }
        rawData.forEach(function (dataPt){
            labels = getLabels(dataPt);
            var count = dataPt.__count || dataPt[self.chart.groupBy[0]+'_count'] || 0;
            var value = isCount ? count : dataPt[self.chart.measure];
            if (value instanceof Array) {
                // when a many2one field is used as a measure AND as a grouped
                // field, bad things happen.  The server will only return the
                // grouped value and will not aggregate it.  Since there is a
                // name clash, we are then in the situation where this value is
                // an array.  Fortunately, if we group by a field, then we can
                // say for certain that the group contains exactly one distinct
                // value for that field.
                value = 1;
            }
            self.chart.dataPoints.push({
                count: count,
                value: value,
                labels: labels,
                originIndex: originIndex,
            });
        });
    },
    /**
     * Helper function (for _processData), turns various values in a usable
     * string form, that we can display in the interface.
     *
     * @private
     * @param {any} value value for the field fieldName received by the read_group rpc
     * @param {string} fieldName
     * @returns {string}
     */
    _sanitizeValue: function (value, fieldName) {
        if (value === false && this.fields[fieldName].type !== 'boolean') {
            return _t("Undefined");
        }
        if (value instanceof Array) {
            return value[1];
        }
        if (fieldName && (this.fields[fieldName].type === 'selection')) {
            var selected = _.where(this.fields[fieldName].selection, {0: value})[0];
            return selected ? selected[1] : value;
        }
        return value;
    },
});

});
