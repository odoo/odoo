odoo.define('web.FieldResume', function (require) {
"use strict";

var time = require('web.time');
var FieldOne2Many = require('web.relational_fields').FieldOne2Many;
var FieldProgressBar = require('web.basic_fields').FieldProgressBar;
var ListRenderer = require('web.ListRenderer');
var field_registry = require('web.field_registry');

var core = require('web.core');
var qweb = core.qweb;
var _t = core._t;

var AbstractGroupedOne2ManyRenderer = ListRenderer.extend({
    /**
     * This abstract renderer is use to render a one2many field in a form view.
     * The records in the one2many field are displayed grouped by a specific field.
     *
     * A concrete renderer can/should set:
     *  - groupBy: field to group records
     *  - dataRowTemplate: template to render a record's data
     *  - groupTitleTemplate (optional): template to render the header row of a group
     *  - addLineButtonTemplate (optional): template to render the 'Add a line' button at the end of each group (edit mode only)
     **/

    groupBy: '', // Field: records are grouped based on this field
    groupTitleTemplate: 'hr_default_group_row', // Template used to render the title row of a group
    dataRowTemplate: '',    // Template used to render a record
    addLineButtonTemplate: 'group_add_item',

     /**
     * @override
     * @private
     * Don't render any header
     */
    _renderHeader: function () {
        return;
    },

     /**
     * @override
     * @private
     * Don't render any footer
     */
    _renderFooter: function () {
        return;
    },

    /**
     * @override
     * @private
     */
    _renderGroupRow: function (display_name) {
        return qweb.render(this.groupTitleTemplate, {display_name: display_name});
    },

    /**
     * This method is meant to be overriten by concrete renderers and
     * is called each time a row is rendered.
     * It is a hook to format record's data before it's given to the qweb template.
     *
     * @private
    */
    _formatData: function (data) {
        return data;
    },

    _renderRow: function (record) {
        return $(qweb.render(this.dataRowTemplate, {
            id: record.id,
            data: this._formatData(record.data),
        }));
    },

    /**
     * This method is meant to be overriten by concrete renderers.
     * Returns a context used for the 'Add a line' button.
     * It's useful to set default values.
     * An 'Add a line' button is added after each group of records.
     * The group passed as parameters allow to set a different context based on the group.
     * If no records exist, group is undefined.
     *
     * @private
    */
    _getCreateLineContext: function (group) {
        return {};
    },

    _renderTrashIcon: function() {
        return qweb.render('hr_trash_button');
    },

    _renderBody: function () {
        var self = this;

        var grouped_by = _.groupBy(this.state.data, function (record) {
            return record.data[self.groupBy].res_id;
        });

        var $body = $('<tbody>');
        _.each(grouped_by, function (group) {
            var groupTitle = group[0].data[self.groupBy].data.display_name;
            var $title_row = $(self._renderGroupRow(groupTitle));
            $body.append($title_row);

            // Render each rows
            _.each(group, function (record) {
                var $row = self._renderRow(record);
                if (self.addTrashIcon) $row.append(self._renderTrashIcon());
                $body.append($row);
            });

            // Get number of cells in a data row to set a correct colspan on the title row
            var number_cells = $body.children('tr:nth-child(2)').children('td').length; // Take the second child because the first is the title row
            $title_row.children('th').attr('colspan', number_cells);

            if (self.addCreateLine) {
                $body.append(qweb.render(self.addLineButtonTemplate, {context: JSON.stringify(self._getCreateLineContext(group))}));
            }
        });

        if ($body.is(':empty') && self.addCreateLine) {
            $body.append(qweb.render(this.addLineButtonTemplate, {context: JSON.stringify(self._getCreateLineContext())}));
        }
        return $body;
    },

});

var ResumeLineRenderer = AbstractGroupedOne2ManyRenderer.extend({

    groupBy: 'line_type_id',
    groupTitleTemplate: 'hr_resume_group_row',
    dataRowTemplate: 'hr_resume_data_row',

    _formatData: function (data) {
        var dateFormat = time.getLangDateFormat();
        var date_start = data.date_start && data.date_start.format(dateFormat) || "";
        var date_end = data.date_end && data.date_end.format(dateFormat) || _t("Current");
        return Object.assign(data, {
            date_start,
            date_end,
        });
    },

    _getCreateLineContext: function (group) {
        var ctx = { default_employee_id: this.getParent().recordData.id };
        return group ? Object.assign({ default_line_type_id: group[0].data[this.groupBy].data.id }, ctx) : ctx;
    },

    _render: function () {
        var self = this;
        this._super().then(function () {
            // Allow to sort records
            self.$el.find('.o_list_view').sortable({
                axis: 'y',
                items: '.o_data_row',
                helper: 'clone',
                handle: '.o_row_handle',
                stop: self._resequence.bind(self),
            });
            self.$el.find('table').removeClass('table table-striped o_list_view_ungrouped');
        });
    },
});


var SkillsRenderer = AbstractGroupedOne2ManyRenderer.extend({

    groupBy: 'skill_type_id',
    dataRowTemplate: 'hr_skill_data_row',

    _renderRow: function (record) {
        var $row = this._super(record);
        // Add progress bar widget at the end of rows
        var $td = $('<td/>', {class: 'o_data_cell'});
        var progress = new FieldProgressBar(this, 'progress', record, {
            current_value: record.data.progress,
            attrs: this.arch.attrs,
        });
        progress.appendTo($td);
        return $row.append($td);
    },

    _getCreateLineContext: function (group) {
        var ctx = { default_employee_id: this.getParent().recordData.id };
        return group ? Object.assign({ default_skill_type_id: group[0].data[this.groupBy].data.id }, ctx) : ctx;
    },
});


var FieldResume = FieldOne2Many.extend({

    /**
     * @override
     * @private
     */
    _getRenderer: function () {
        return ResumeLineRenderer;
    },
});

var FieldSkills = FieldOne2Many.extend({

    /**
     * @override
     * @private
     */
    _getRenderer: function () {
        return SkillsRenderer;
    },
});

field_registry.add('hr_resume', FieldResume);
field_registry.add('hr_skills', FieldSkills);

return FieldResume;

});
