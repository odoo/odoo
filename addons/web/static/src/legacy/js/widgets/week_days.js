odoo.define('web.WeekDays', function (require) {
    'use strict';

    const CustomCheckbox = require('web.CustomCheckbox');
    const Registry = require('web.widgetRegistry');
    const utils = require('web.utils');
    const { LegacyComponent } = require("@web/legacy/legacy_component");

    const { onWillUpdateProps, useState } = owl;

    class WeekDays extends LegacyComponent {
        setup() {
            this.weekdaysShort = [];
            this._sortWeekdays();
            this.state = useState({ days: this._prepareData(this.props.record.data) });
            this.mode = this.props.options.mode;

            onWillUpdateProps(this.onWillUpdateProps);
        }

        /**
         * @param {Object} nextProps
         * @param {Object} nextProps.record
         */
        async onWillUpdateProps(nextProps) {
            this.state.days = this._prepareData(nextProps.record.data);
            this.mode = nextProps.options.mode;
        }

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
         * Prepares weekdays data for state
         * @private
         * @param {Object} data
         */
        _prepareData(data) {
            const weekdays = {};
            this.weekdaysShort.forEach((day) => {
                weekdays[day] = {
                    id: `${day}-${utils.generateID()}`,
                    value: data[day],
                };
            });
            return weekdays;
        }
        /**
         * Generates short week days as per start of the week of language
         * @private
         */
        _sortWeekdays() {
            const weekStart = this.env._t.database.parameters.week_start;
            const weekdaysShort = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'];
            const slicedArray1 = weekdaysShort.slice(weekStart - 1, weekdaysShort.length);
            const slicedArray2 = weekdaysShort.slice(0, weekStart - 1);
            this.weekdaysShort = slicedArray1.concat(slicedArray2);
        }

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        /**
         * @private
         * @param {MouseEvent} ev
         */
        _onChange(checked, field) {
            this.trigger('field-changed', {
                dataPointID: this.props.record.id,
                changes: { [field.split("-")[0]]: checked },
            });
        }
    }

    WeekDays.components = { CustomCheckbox };
    WeekDays.template = "web.RecurrentTask";
    WeekDays.fieldDependencies = {
        sun: {type: 'boolean'},
        mon: {type: 'boolean'},
        tue: {type: 'boolean'},
        wed: {type: 'boolean'},
        thu: {type: 'boolean'},
        fri: {type: 'boolean'},
        sat: {type: 'boolean'},
    };

    Registry.add('week_days', WeekDays);

    return WeekDays;
});
