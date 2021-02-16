odoo.define('hr_work_entry_contract.work_entries_gantt', function(require) {
    'use strict';

    var WorkEntryControllerMixin = require('hr_work_entry_contract.WorkEntryControllerMixin');
    var GanttView = require('web_gantt.GanttView');
    var GanttController = require('web_gantt.GanttController');
    var viewRegistry = require('web.view_registry');


    var WorkEntryGanttController = GanttController.extend(WorkEntryControllerMixin, {
        events: _.extend({}, WorkEntryControllerMixin.events, GanttController.prototype.events),


        _renderButtonsQWeb: function() {
            return this._super.apply(this, arguments).append(this._renderWorkEntryButtons());
        },
        _fetchRecords: function () {
            return this.model.ganttData.records;
        },
        _fetchFirstDay: function () {
            return this.model.ganttData.startDate;
        },
        _fetchLastDay: function () {
            return this.model.ganttData.stopDate;
        },
        _displayWarning: function ($warning) {
            this.$('.o_gantt_view').before($warning);
        },
    });

    var WorkEntryGanttView = GanttView.extend({
        config: _.extend({}, GanttView.prototype.config, {
            Controller: WorkEntryGanttController,
        }),
    });

    viewRegistry.add('work_entries_gantt', WorkEntryGanttView);

    return WorkEntryGanttController;

});
