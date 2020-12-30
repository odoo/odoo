odoo.define('project.project_update_widget', function (require) {
    "use strict";
    
    var time = require('web.time');
    const fieldRegistry = require('web.field_registry');
    const ListRenderer = require('web.ListRenderer');
    const { FieldOne2Many } = require('web.relational_fields');
    const { _lt, qweb } = require('web.core');
    
    var UpdatesLineRenderer = ListRenderer.extend({
        dataRowTemplate: 'project.status_update_data_row',
        countRows: 0,

        /**
         * Renders a empty header
         *
         * @override
         * @private
         */
        _renderHeader: function () {
            return $('<thead/>');
        },

            /**
         * Renders a empty footer
         *
         * @override
         * @private
         */
        _renderFooter: function () {
            return $('<tfoot/>');
        },

        _formatData: function (data) {
            var dateFormat = time.getLangDateFormat();
            var date = data.date && data.date.format(dateFormat) || "";
            return _.extend(data, {
                date: date,
                status_id: data.status_id.data.display_name,
            });
        },

        _renderRow: function (record) {
            this.countRows++;
            return $(qweb.render(this.dataRowTemplate, {
                id: record.id,
                data: this._formatData(record.data),
                is_last: this.countRows === this.state.count,
                is_first: this.countRows === 1,
            }));
        },

        _render: function () {
            var self = this;
            this.countRows = 0;
            return this._super().then(function () {
                self.$el.find('table').removeClass('table-striped o_list_table');
                self.$el.find('table').addClass('o_project_status_table table-borderless');
            });
        },
    });

    var ProjectUpdateField = FieldOne2Many.extend({
        /**
         * @override
         * @private
         */
        _getRenderer: function () {
            return UpdatesLineRenderer;
        },
    });
    
    fieldRegistry.add('one2many_project_updates', ProjectUpdateField);
    
    return ProjectUpdateField;
    
});
