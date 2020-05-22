odoo.define('mrp.mrp_state_owl', function (require) {
    "use strict";

    const AbstractFieldOwl = require('web.AbstractFieldOwl');
    const fieldRegistryOwl = require('web.field_registry_owl');
    const time = require('web.time');

    const { xml } = owl.tags;

    /**
     * This component is used to display the availability on a workorder.
     */
    class OWLSetBulletStatus extends AbstractFieldOwl { }

    OWLSetBulletStatus.template = 'mrp.OWLSetBulletStatus';


    class OWLTimeCounter extends AbstractFieldOwl {

        async willStart() {
            const result = await this.env.services.rpc({
                model: 'mrp.workcenter.productivity',
                method: 'search_read',
                domain: [
                    ['workorder_id', '=', this.record.data.id],
                ],
            });
            if (this.mode === 'readonly') {
                const currentDate = new Date();
                this.duration = 0;
                result.forEach(data => {
                    this.duration += data.date_end ?
                        this._getDateDifference(data.date_start, data.date_end) :
                        this._getDateDifference(time.auto_str_to_date(data.date_start), currentDate);
                });
            }
        }

        mounted() {
            this._startTimeCounter();
        }

        patched() {
            this._startTimeCounter();
        }

        willUnmount() {
            clearTimeout(this.timer);
        }

        //--------------------------------------------------------------------------
        // Getters
        //--------------------------------------------------------------------------

        /**
         * @override
         */
        get isSet() {
            return true;
        }

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
        * Compute the difference between two dates.
        *
        * @private
        * @param {string} dateStart
        * @param {string} dateEnd
        * @returns {integer} the difference in millisecond
        */
        _getDateDifference(dateStart, dateEnd) {
            return moment(dateEnd).diff(moment(dateStart));
        }

        /**
         * @private
         */
        _startTimeCounter() {
            const self = this;
            clearTimeout(this.timer);
            if (this.record.data.is_user_working) {
                this.timer = setTimeout(function () {
                    self.duration += 1000;
                    self._startTimeCounter();
                }, 1000);
            } else {
                clearTimeout(this.timer);
            }
            this.el.textContent = moment.utc(this.duration).format("HH:mm:ss");
        }
    }

    OWLTimeCounter.template = xml`<span/>`;

    fieldRegistryOwl
        .add('mrp_time_counter', OWLTimeCounter)
        .add('bullet_state', OWLSetBulletStatus);

});
