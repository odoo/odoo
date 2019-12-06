odoo.define('hr_timesheet.timer', function (require) {
"use strict";

var fieldRegistry = require('web.field_registry');
var AbstractField = require('web.AbstractField');

var TimerFieldWidget = AbstractField.extend({

    /**
     * @override
     * @private
     */
    isSet: function () {
        return true;
    },
    /**
     * @private
     */
    _getDuration: function (dateStart, datePause) {
        if (datePause && dateStart) {
            return moment(datePause).diff(moment(dateStart));
        }
        if (dateStart) {
            return moment().diff(moment(dateStart));
        }
        else return 0;
    },
    /**
     * @override
     * @private
     */
    _render: function () {
        this._startTimeCounter();

    },
    /**
     * @override
     */
    destroy: function () {
        this._super.apply(this, arguments);
        clearTimeout(this.timer);
    },
    /**
     * @private
     */
    _startTimeCounter: function () {
        var self = this;
        clearTimeout(this.timer);
        if (self.record.data.timer_start) {
            this.timer = setTimeout(function () {
                self._startTimeCounter();
            }, 1000);
            this.$el.text(moment.utc(self._getDuration(self.record.data.timer_start, self.record.data.timer_pause)).format("HH:mm:ss"));
        } else if (!self.record.data.timer_pause){
            clearTimeout(this.timer);
        }
    },
});

fieldRegistry.add('timesheet_timer', TimerFieldWidget);

});
