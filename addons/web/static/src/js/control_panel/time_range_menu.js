odoo.define('web.TimeRangeMenu', function (require) {
    "use strict";

    const { COMPARISON_TIME_RANGE_OPTIONS, DEFAULT_PERIOD, TIME_RANGE_OPTIONS } = require('web.searchUtils');
    const DropdownMenu = require('web.DropdownMenu');
    const { useModel } = require('web.model');

    // Used to provide unique ids to its template elements.
    let timeRangeMenuId = 0;

    /**
     * 'Time ranges' menu
     *
     * Component used to create a time range from a field, a given range and optionally
     * another field to make a comparison.
     *
     * The component template overrides the dropdownmenu to keep the basic behaviours
     * (opening/closing, layout). The template itself iis a set of labels/inputs
     * used to select the field and range. There is also a checkbox used to determine
     * whether to render the comparison range field selection (input).
     * @extends DropdownMenu
     */
    class TimeRangeMenu extends DropdownMenu {
        constructor() {
            super(...arguments);
            this.model = useModel('controlPanelModel');

            this.domId = timeRangeMenuId++;
            this.fields = Object.values(this.props.fields)
                .filter(field => this._validateField(field));
            this.periodOptions = TIME_RANGE_OPTIONS;
            this.comparisonTimeRangeOptions = COMPARISON_TIME_RANGE_OPTIONS;
            this.periodGroups = Object.values(this.periodOptions).reduce((acc, o) => {
                if (!acc.includes(o.groupNumber)) {
                    acc.push(o.groupNumber);
                }
                return acc;
            }, []);
            const activeTimeRange = this.model.getFiltersOfType('timeRange').find(
                timeRange => timeRange.isActive
            );
            Object.assign(this.state, {
                fieldName: this.fields[0] && this.fields[0].name,
                rangeId: DEFAULT_PERIOD,
            }, activeTimeRange);
        }

        //---------------------------------------------------------------------
        // Getters
        //---------------------------------------------------------------------

        /**
         * @override
         */
        get title() {
            return this.env._t("Time Ranges");
        }

        //---------------------------------------------------------------------
        // Private
        //---------------------------------------------------------------------

        /**
         * @private
         * @param {Object} field
         * @returns {boolean}
         */
        _validateField(field) {
            return field.sortable &&
                ['date', 'datetime'].includes(field.type);
        }

        //---------------------------------------------------------------------
        // Handlers
        //---------------------------------------------------------------------

        /**
         * @private
         */
        _onApply() {
            this.model.dispatch('activateTimeRange',
                this.state.fieldName,
                this.state.rangeId,
                this.state.comparisonRangeId
            );
        }

        /**
         * @private
         */
        _onCheckboxClick() {
            if (!this.state.comparisonRangeId) {
                this.state.comparisonRangeId = 'previous_period'; // default
            } else {
                delete this.state.comparisonRangeId;
            }
        }
    }

    TimeRangeMenu.defaultProps = Object.assign({}, DropdownMenu.defaultProps, {
        icon: 'fa fa-calendar',
    });
    TimeRangeMenu.props = Object.assign({}, DropdownMenu.props, {
        fields: Object,
    });
    TimeRangeMenu.template = 'web.TimeRangeMenu';

    return TimeRangeMenu;
});
