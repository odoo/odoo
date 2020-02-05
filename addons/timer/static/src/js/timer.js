odoo.define('timer.timer', function (require) {
"use strict";

var fieldRegistry = require('web.field_registry');
var AbstractField = require('web.AbstractField');
var Timer = require('timer.Timer');

var TimerFieldWidget = AbstractField.extend({

    /**
     * @override
     * @private
     */
    isSet: function () {
        return true;
    },
    /**
     * @override
     * @private
     */
    _render: function () {
        this._super.apply(this, arguments);
        this._startTimeCounter();
    },
    /**
     * @override
     */
    destroy: function () {
        this._super.apply(this, arguments);
        clearInterval(this.timer);
    },
    /**
     * @private
     */
    _startTimeCounter: async function () {
        if (this.record.data.timer_start) {
            const serverTime = this.record.data.timer_pause || await this._getServerTime();
            this.time = Timer.createTimer(0, this.record.data.timer_start, serverTime);
            this.$el.text(this.time.toString());
            this.timer = setInterval(() => {
                if (this.record.data.timer_pause) {
                    clearInterval(this.timer);
                } else {
                    this.time.addSecond();
                    this.$el.text(this.time.toString());
                }
            }, 1000);
        } else if (!this.record.data.timer_pause){
            clearInterval(this.timer);
        }
    },
    _getServerTime: function () {
        return this._rpc({
            model: 'timer.timer',
            method: 'get_server_time',
            args: []
        });
    }
});

fieldRegistry.add('timer_timer', TimerFieldWidget);

});
