/** @odoo-module **/

import viewRegistry from "web.view_registry";
import ListModel from "web.ListModel";
import ListRenderer from "web.ListRenderer";
import ListView from "web.ListView";

function _findRecordsInState(entrypoint, result = []) {
    if (entrypoint && entrypoint.type === "list") {
        for (const element of entrypoint.data.values()) {
            _findRecordsInState(element, result);
        }
    } else if (entrypoint && entrypoint.type === "record") {
        result.push(entrypoint);
    }
    return result;
}

function _bindLazyColumnToState(entrypoint, lazyColumns, values, startRequestTime) {
    let records = _findRecordsInState(entrypoint);
    for (const recordData of records.values()) {
        // keep track of request start time (in _fetchRecord) when we fetch a particular record (can happens we
        // modify the priority field) to avoids to erase the old data if the lazy loaded finished after.
        if (startRequestTime && recordData.specialData && recordData.specialData.lastUpdateLazy && startRequestTime <= recordData.specialData.lastUpdateLazy){
            continue
        }
        for (const lazyCol of lazyColumns) {
            recordData.data[lazyCol] =
                (values && values[recordData.data.id] && values[recordData.data.id][lazyCol]) ||
                false;
        }
    }
}

function _getLazyColumns(fieldsInfo) {
    const lazyColumns = [];
    if (!fieldsInfo) {
        return lazyColumns;
    }
    for (const [key, value] of Object.entries(fieldsInfo)) {
        if (value.options && value.options.lazy) {
            lazyColumns.push(key);
        }
    }
    return lazyColumns;
}

const LazyColumnListModel = ListModel.extend({
    /**
     * Avoid to fetch lazy fields by filter-out for the model
     * (`_searchReadUngroupedList`), and let the controller manage it.
     *
     * @param {Object} element an element from the localData
     * @param {Object} [options]
     * @param {Object} [options.viewType] current viewType. If not set, we will
     *   assume main viewType from the record
     * @returns {string[]} the list of field names
     */
    _getFieldNames: function (element, options) {
        const res = this._super.apply(this, arguments);
        if (element.type !== "list") {
            // lazy is only for list type element
            return res;
        }
        const fieldsInfo = element.fieldsInfo;
        const viewType = (options && options.viewType) || element.viewType;
        const lazyColumns = _getLazyColumns(fieldsInfo[viewType]);
        return res.filter((column) => !lazyColumns.includes(column));
    },

    _makeDataPoint: function () {
        // Should put the lazy column to work with decoration
        const dataPoint = this._super.apply(this, arguments);
        if (dataPoint.type === "record" && dataPoint.fieldsInfo) {
            const fieldsInfo = dataPoint.fieldsInfo[dataPoint.viewType];
            const lazyColumn = _getLazyColumns(fieldsInfo);
            _bindLazyColumnToState(dataPoint, lazyColumn);
        }
        return dataPoint;
    },
    
    _fetchRecord: function(record, options) {
        record.specialData.lastUpdateLazy = Date.now();
        return this._super.apply(this, arguments);
    }
});

const LazyColumnListRenderer = ListRenderer.extend({
    init: function () {
        this.currentNbLazyRpc = 0;
        return this._super.apply(this, arguments);
    },

    _lazyLoad: async function (state, lazyColumns) {
        const startRequestTime = Date.now()
        const res = await this._rpc(
            {
                model: state.model,
                method: "search_read",
                args: [state.domain, lazyColumns],
            },
            { shadow: true }
        );
        const resById = {};
        for (const element of res.values()) {
            resById[element.id] = {};
            for (const lazyCol of lazyColumns) {
                resById[element.id][lazyCol] = element[lazyCol];
            }
        }
        _bindLazyColumnToState(this.state, lazyColumns, resById, startRequestTime);
        this.currentNbLazyRpc -= 1;
        // Render only the lazy columns
        for (const lazyCol of lazyColumns) {
            const node = this.columns.find((colAttribute) => colAttribute.attrs.name === lazyCol);
            if (!node) {
                continue;
            }
            const indexNode = this.columns.findIndex(
                (colAttribute) => colAttribute.attrs.name === lazyCol
            );
            const $columnHeader = this.$el.find(`th[data-name='${lazyCol}']`);
            $columnHeader.replaceWith(this._renderHeaderCell(node));
            const $cellsLazy = this.$el.find(`.o_data_cell[name='${lazyCol}']`);
            for (let i = 0; i <= $cellsLazy.length; i++) {
                const $cell = $($cellsLazy[i]);
                const idRecord = $cell.parent().data("id");
                const record = _findRecordsInState(this.state).find((rec) => rec.id === idRecord);
                if (record) {
                    $cell.replaceWith(
                        this._renderBodyCell(record, node, indexNode, { mode: "readonly" })
                    );
                }
            }
        }
    },

    async _render() {
        const lazyColumns = _getLazyColumns(this.state.fieldsInfo[this.state.type]);
        const lazyVisible = lazyColumns.some((col) => {
            return !!this.columns.find((colAttribute) => colAttribute.attrs.name === col);
        });
        const lazyLoad = lazyVisible && this.state.res_ids.length > 0;
        if (lazyLoad) {
            this.currentNbLazyRpc += 1;
        }
        const res = await this._super(...arguments);
        if (lazyLoad) {
            this._lazyLoad(this.state, lazyColumns);
        }
        return res;
    },

    _isLazyNode: function (node) {
        try {
            if (JSON.parse(node.attrs.options).lazy) {
                return true;
            }
        } catch (e) {
            return false;
        }
        return false;
    },

    _renderBodyCell: function (record, node) {
        const $res = this._super.apply(this, arguments);
        const lazyColumns = _getLazyColumns(this.state.fieldsInfo[this.state.type]);
        if (this._isLazyNode(node)) {
            // Decorations doesn't work for lazy column because the evalContext isn't updated and it is a readonly attribute
            // Then a lazy fields can be only used in a other lazy fields decoration.
            const extraData = {};
            for (const col of lazyColumns) {
                extraData[col] = record.data[col];
            }
            const evalContext = Object.assign({}, record.evalContext, extraData);
            for (const [cssClass, expr] of Object.entries(this.fieldDecorations[node.attrs.name])) {
                $res.toggleClass(cssClass, py.PY_isTrue(py.evaluate(expr, evalContext)));
            }
        }
        return $res;
    },

    _renderHeaderCell: function (node) {
        const $res = this._super.apply(this, arguments);
        if (this._isLazyNode(node)) {
            const $spin = $('<i class="fa fa-refresh fa-spin m-1"/>');
            if (this.currentNbLazyRpc == 0) {
                $spin.addClass("invisible");
            }
            $res.find(":last").before($spin);
        }
        return $res;
    },
});

const LazyColumnList = ListView.extend({
    config: Object.assign({}, ListView.prototype.config, {
        Renderer: LazyColumnListRenderer,
        Model: LazyColumnListModel,
    }),
});

viewRegistry.add("lazy_column_list", LazyColumnList);

export default LazyColumnList;
