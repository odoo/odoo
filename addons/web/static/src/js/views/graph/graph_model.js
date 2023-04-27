odoo.define('web.GraphModel', function (require) {
"use strict";

var core = require('web.core');
const { DEFAULT_INTERVAL, rankInterval } = require('web.searchUtils');

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
    __get: function () {
        return Object.assign({ isSample: this.isSampleModel }, this.chart);
    },
    /**
     * Initial loading.
     *
     * @todo All the work to fall back on the graph_groupbys keys in the context
     * should be done by the graphView I think.
     *
     * @param {Object} params
     * @param {Object} params.context
     * @param {Object} params.fields
     * @param {string[]} params.domain
     * @param {string[]} params.groupBys a list of valid field names
     * @param {string[]} params.groupedBy a list of valid field names
     * @param {boolean} params.stacked
     * @param {string} params.measure a valid field name
     * @param {'pie'|'bar'|'line'} params.mode
     * @param {string} params.modelName
     * @param {Object} params.timeRanges
     * @returns {Promise} The promise does not return a handle, we don't need
     *   to keep track of various entities.
     */
    __load: function (params) {
        var groupBys = params.context.graph_groupbys || params.groupBys;
        this.initialGroupBys = groupBys;
        this.fields = params.fields;
        this.modelName = params.modelName;
        this.chart = Object.assign({
            context: params.context,
            dataPoints: [],
            domain: params.domain,
            groupBy: params.groupedBy.length ? params.groupedBy : groupBys,
            measure: params.context.graph_measure || params.measure,
            mode: params.context.graph_mode || params.mode,
            origins: [],
            stacked: params.stacked,
            timeRanges: params.timeRanges,
            orderBy: params.orderBy
        });

        this._computeDerivedParams();

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
     * @param {boolean} [params.stacked]
     * @param {Object} [params.context]
     * @param {string[]} [params.domain]
     * @param {string[]} [params.groupBy]
     * @param {string} [params.measure] a valid field name
     * @param {string} [params.mode] one of 'bar', 'pie', 'line'
     * @param {Object} [params.timeRanges]
     * @returns {Promise}
     */
    __reload: function (handle, params) {
        if ('context' in params) {
            this.chart.context = params.context;
            this.chart.groupBy = params.context.graph_groupbys || this.chart.groupBy;
            this.chart.measure = params.context.graph_measure || this.chart.measure;
            this.chart.mode = params.context.graph_mode || this.chart.mode;
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
        if ('timeRanges' in params) {
            this.chart.timeRanges = params.timeRanges;
        }

        this._computeDerivedParams();

        if ('mode' in params) {
            this.chart.mode = params.mode;
            return Promise.resolve();
        }
        if ('stacked' in params) {
            this.chart.stacked = params.stacked;
            return Promise.resolve();
        }
        if ('orderBy' in params) {
            this.chart.orderBy = params.orderBy;
            return Promise.resolve();
        }
        return this._loadGraph();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Compute this.chart.processedGroupBy, this.chart.domains, this.chart.origins,
     * and this.chart.comparisonFieldIndex.
     * Those parameters are determined by this.chart.timeRanges, this.chart.groupBy, and this.chart.domain.
     *
     * @private
     */
    _computeDerivedParams: function () {
        this.chart.processedGroupBy = this._processGroupBy(this.chart.groupBy);

        const { range, rangeDescription, comparisonRange, comparisonRangeDescription, fieldName } = this.chart.timeRanges;
        if (range) {
            this.chart.domains = [
                this.chart.domain.concat(range),
                this.chart.domain.concat(comparisonRange),
            ];
            this.chart.origins = [rangeDescription, comparisonRangeDescription];
            const groupBys = this.chart.processedGroupBy.map(function (gb) {
                return gb.split(":")[0];
            });
            this.chart.comparisonFieldIndex = groupBys.indexOf(fieldName);
        } else {
            this.chart.domains = [this.chart.domain];
            this.chart.origins = [""];
            this.chart.comparisonFieldIndex = -1;
        }
    },
    /**
     * @override
     */
    _isEmpty() {
        return this.chart.dataPoints.length === 0;
    },
    /**
     * Fetch and process graph data.  It is basically a(some) read_group(s)
     * with correct fields for each domain.  We have to do some light processing
     * to separate date groups in the field list, because they can be defined
     * with an aggregation function, such as my_date:week.
     *
     * @private
     * @returns {Promise}
     */
    _loadGraph: function () {
        var self = this;
        this.chart.dataPoints = [];
        var groupBy = this.chart.processedGroupBy;
        var fields = _.map(groupBy, function (groupBy) {
            return groupBy.split(':')[0];
        });
        const loadId = this.loadId ? ++this.loadId : 1;
        this.loadId = loadId;

        if (this.chart.measure !== '__count__') {
            if (this.fields[this.chart.measure].type === 'many2one') {
                fields = fields.concat(this.chart.measure + ":count_distinct");
            }
            else {
                fields = fields.concat(this.chart.measure);
            }
        }

        var context = _.extend({fill_temporal: true}, this.chart.context);

        var proms = [];
        this.chart.domains.forEach(function (domain, originIndex) {
            proms.push(self._rpc({
                model: self.modelName,
                method: 'read_group',
                context: context,
                domain: domain,
                fields: fields,
                groupBy: groupBy,
                lazy: false,
            }).then(self._processData.bind(self, originIndex, loadId)));
        });
        return Promise.all(proms);
    },
    /**
     * Since read_group is insane and returns its result on different keys
     * depending of some input, we have to normalize the result.
     * Each group coming from the read_group produces a dataPoint
     *
     * @private
     * @param {number} originIndex
     * @param {any} rawData result from the read_group
     */
    _processData: function (originIndex, loadId, rawData) {
        if (loadId < this.loadId) {
            return;
        }
        var self = this;
        var isCount = this.chart.measure === '__count__';
        var labels;

        function getLabels (dataPt) {
            return self.chart.processedGroupBy.map(function (field) {
                return self._sanitizeValue(dataPt[field], field.split(":")[0]);
            });
        }
        rawData.forEach(function (dataPt){
            labels = getLabels(dataPt);
            var count = dataPt.__count || dataPt[self.chart.processedGroupBy[0]+'_count'] || 0;
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
                resId: dataPt[self.chart.groupBy[0]] instanceof Array ? dataPt[self.chart.groupBy[0]][0] : -1,
                count: count,
                domain: dataPt.__domain,
                value: value,
                labels: labels,
                originIndex: originIndex,
            });
        });
    },
    /**
     * Process the groupBy parameter in order to keep only the finer interval option for
     * elements based on date/datetime field (e.g. 'date:year'). This means that
     * 'week' is prefered to 'month'. The field stays at the place of its first occurence.
     * For instance,
     * ['foo', 'date:month', 'bar', 'date:week'] becomes ['foo', 'date:week', 'bar'].
     *
     * @private
     * @param {string[]} groupBy
     * @returns {string[]}
     */
    _processGroupBy: function(groupBy) {
        const groupBysMap = new Map();
        for (const gb of groupBy) {
            let [fieldName, interval] = gb.split(':');
            const field = this.fields[fieldName];
            if (['date', 'datetime'].includes(field.type)) {
                interval = interval || DEFAULT_INTERVAL;
            }
            if (groupBysMap.has(fieldName)) {
                const registeredInterval = groupBysMap.get(fieldName);
                if (rankInterval(registeredInterval) < rankInterval(interval)) {
                    groupBysMap.set(fieldName, interval);
                }
            } else {
                groupBysMap.set(fieldName, interval);
            }
        }
        return [...groupBysMap].map(([fieldName, interval]) => {
            if (interval) {
                return `${fieldName}:${interval}`;
            }
            return fieldName;
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
