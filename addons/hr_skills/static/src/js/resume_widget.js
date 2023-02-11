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
     * Don't freeze the columns because as the header is empty, the algorithm
     * won't work.
     *
     * @override
     * @private
     */
    _freezeColumnWidths: function () {},

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

    _renderRow: function (record, isLast) {
        return $(qweb.render(this.dataRowTemplate, {
            id: record.id,
            data: this._formatData(record.data),
            is_last: isLast,
        }));
    },

    /**
     * This method is meant to be overridden by concrete renderers.
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

    _renderAddItemButton: function (group) {
        return qweb.render(this.addLineButtonTemplate, {
            context: JSON.stringify(this._getCreateLineContext(group)),
        });
    },

    _renderBody: function () {
        var self = this;

        var grouped_by = _.groupBy(this.state.data, function (record) {
            return record.data[self.groupBy].res_id;
        });

        var groupTitle;
        var $body = $('<tbody>');
        for (var key in grouped_by) {
            var group = grouped_by[key];
            if (key === 'undefined') {
                groupTitle = _t("Other");
            } else {
                groupTitle = group[0].data[self.groupBy].data.display_name;
            }
            var $title_row = $(self._renderGroupRow(groupTitle));
            $body.append($title_row);

            // Render each rows
            group.forEach(function (record, index) {
                var isLast = (index + 1 === group.length);
                var $row = self._renderRow(record, isLast);
                if (self.addTrashIcon) $row.append(self._renderTrashIcon());
                $body.append($row);
            });

            if (self.addCreateLine) {
                $title_row.find('.o_group_name').append(self._renderAddItemButton(group));
            }
        }

        if ($body.is(':empty') && self.addCreateLine) {
            $body.append(this._renderAddItemButton());
        }
        return $body;
    },

    /**
     * This function enables the top right menu on list views to hide/show fields or, when studio is installed,
     *  edit the view's content.
     * For this widget we do not want it at all.
     *
     * @override
     * @private
     * @returns {boolean}
     */
     _shouldRenderOptionalColumnsDropdown: function () {
         return false;
     }
});

var ResumeLineRenderer = AbstractGroupedOne2ManyRenderer.extend({

    groupBy: 'line_type_id',
    groupTitleTemplate: 'hr_resume_group_row',
    dataRowTemplate: 'hr_resume_data_row',

    _formatData: function (data) {
        var dateFormat = time.getLangDateFormat();
        var date_start = data.date_start && data.date_start.format(dateFormat) || "";
        var date_end = data.date_end && data.date_end.format(dateFormat) || _t("Current");
        return _.extend(data, {
            date_start: date_start,
            date_end: date_end,
        });
    },

    _getCreateLineContext: function (group) {
        var ctx = this._super(group);
        return group ? _.extend({default_line_type_id: group[0].data[this.groupBy] && group[0].data[this.groupBy].data.id || ""}, ctx) : ctx;
    },

    _render: function () {
        var self = this;
        return this._super().then(function () {
            self.$el.find('table').removeClass('table-striped o_list_table_ungrouped');
            self.$el.find('table').addClass('o_resume_table table-borderless');
        });
    },
});


var SkillsRenderer = AbstractGroupedOne2ManyRenderer.extend({

    groupBy: 'skill_type_id',
    dataRowTemplate: 'hr_skill_data_row',

    _renderRow: function (record) {
        var $row = this._super(record);
        // Add progress bar widget at the end of rows
        var $td = $('<td/>', {class: 'o_data_cell o_skill_cell'});
        var progress = new FieldProgressBar(this, 'level_progress', record, {
            current_value: record.data.level_progress,
            attrs: this.arch.attrs,
        });
        progress.appendTo($td);
        return $row.append($td);
    },

    _getCreateLineContext: function (group) {
        var ctx = this._super(group);
        return group ? _.extend({ default_skill_type_id: group[0].data[this.groupBy].data.id }, ctx) : ctx;
    },

    _render: function () {
        var self = this;
        return this._super().then(function () {
            self.$el.find('table').toggleClass('table-striped');
        });
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
