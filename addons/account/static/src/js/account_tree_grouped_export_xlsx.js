odoo.define('account.tree.export_xlsx', function (require) {
"use strict";

var ListController = require('web.ListController');
var field_utils = require('web.field_utils');
var framework = require('web.framework');
var session = require('web.session');

ListController.include({
    /**
     * @override
     *
     * Adding export xlsx button if there is groupby
     */
    renderButtons: function ($node) {
        this._super.apply(this, arguments);
        var state = this.model.get(this.handle);
        if (state.groupedBy.length > 0 && this.$el.find(".account_export_as_xlsx").length) {
            var $exporttButton = $('<button class="btn btn-secondary o_export_xslx" type="button">Export (XLSX)</button>');
            $exporttButton.on('click', this._onClickExportXLSX.bind(this));
            $exporttButton.appendTo($node.find(".o_list_buttons"));
        }
    },
    /**
     * @override
     */
    updateControlPanel: function () {
        this._super.apply(this, arguments);
        var state = this.model.get(this.handle);
        if (state.groupedBy.length > 0 && this.$el.find(".account_export_as_xlsx").length) {
            this.$buttons.find(".o_export_xslx").prop("disabled", state.data.length <= 0);
        }
    },
    /**
     * @private
     *
     * Generate data array with grouped list and their child records.
     *
     * @param {Array} array for state data
     * @param {Array} columns to process
     * @param {Object} fields object with property
     */
    _generateData: function (dataArray, columns, fields) {
        var self = this;
        columns = columns.concat("id");
        var records = [];
        _.each(dataArray, function (data) {
            var dataValues = { type: data.type };
            if (data.type == "list") { // Grouped List
                dataValues = _.extend(dataValues, {
                    value: data.value,
                    aggregateValues: data.aggregateValues,
                    data: data.data ? self._generateData(data.data, columns, fields) : []
                });
            }
            if (data.type == "record") {
                dataValues['record'] = _.mapObject(_.pick(data.data, columns), function (obj, key) {
                    if (_.isObject(obj) && obj.data) {
                        // For m2m or o2m if any
                        if (_.isArray(obj.data) && obj.data) {
                            return _.map(obj.data, function (val) {
                                return val.data.display_name;
                            }).join(", ");
                        }
                    }
                    var field = fields[key];
                    var formattedValue = obj;
                    if (!_.contains(["integer", "float", "monetary"], field.type)) {
                        formattedValue = field_utils.format[field.type](obj, field, {
                            data: data.data,
                            escape: false
                        });
                        if (_.isString(formattedValue)) {
                            formattedValue = formattedValue.replace(/&nbsp;/g, ' ');
                        }
                    }
                    return formattedValue;
                });
            }
            records.push(dataValues);
        });
        return records;
    },
    /**
     * @private
     *
     * @param {Event} ev
     */
    _onClickExportXLSX: function (ev) {
        var self = this;
        var state = this.model.get(this.handle);
        var fields = state.fields;
        var renderColumns = _.values(_.mapObject(this.renderer.columns, function (value) {
            if (value.attrs.string) {
                fields[value.attrs.name].string = value.attrs.string;
            }
            return value.attrs.name;
        }));
        var rawData = this._generateData(state.data, renderColumns, fields);
        var aggregates = {};
        _.each(this.renderer.columns, function (column) {
            if ('aggregate' in column) {
                aggregates[column.attrs.name] = column.aggregate;
            }
        });
        var params = {
            columns: renderColumns,
            fields: _.pick(fields, renderColumns),
            rows: rawData,
            aggregates: aggregates,
            title: this.getTitle()
        }
        framework.blockUI();
        session.get_file({
            url: '/web/export_xlsx/export',
            data: {data: JSON.stringify(params)},
            complete: framework.unblockUI,
            error: () => this.call('crash_manager', 'rpc_error', ...arguments),
        });
    },
});

});
