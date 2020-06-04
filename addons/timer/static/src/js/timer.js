odoo.define('timer.timer', function (require) {
    "use strict";

    const { xml } = owl.tags;
    const AbstractFieldOwl = require('web.AbstractFieldOwl');
    const fieldRegistryOwl = require('web.field_registry_owl');
    const Timer = require('timer.Timer');

    class TimerFieldWidget extends AbstractFieldOwl {

        constructor() {
            super(...arguments);
        }

        mounted() {
            this._startTimeCounter();
        }

        willUnmount() {
            clearInterval(this.timer);
        }

        /**
         * @override
         * @private
         */
        isSet() {
            return true;
        }

        /**
         * @private
         */
        async _startTimeCounter() {
            if (this.record.data.timer_start) {
                const serverTime = this.record.data.timer_pause || await this._getServerTime();
                this.time = Timer.createTimer(0, this.record.data.timer_start, serverTime);
                this.el.textContent = this.time.toString();
                this.timer = setInterval(() => {
                    if (this.record.data.timer_pause) {
                        clearInterval(this.timer);
                    } else {
                        this.time.addSecond();
                        this.el.textContent = this.time.toString();
                    }
                }, 1000);
            } else if (!this.record.data.timer_pause){
                clearInterval(this.timer);
            }
        }

        _getServerTime() {
            return this.env.services.rpc({
                model: 'timer.timer',
                method: 'get_server_time',
                args: []
            });
        }
    }

    TimerFieldWidget.template = xml`<div/>`;

    fieldRegistryOwl.add('timer_timer', TimerFieldWidget);

});