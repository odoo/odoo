import { Component, useState, useRef, onMounted } from "@odoo/owl";
import { BottomSheet } from "@web/core/bottom_sheet/bottom_sheet";
import { Time } from "@web/core/l10n/time";
import { useDebounced } from "@web/core/utils/timing";
import { useService } from "@web/core/utils/hooks";

/**
 * Bottom sheet content for time picker on mobile
 * Displays three scrollable columns for hours, minutes, and seconds
 */
export class TimePickerBottomSheet extends Component {
    static components = { BottomSheet };
    static template = "web.TimePickerBottomSheet";
    static props = {
        id: { type: Number, optional: true },
        value: { type: Time, optional: true },
        showSeconds: { type: Boolean, optional: true },
        minutesRounding: { type: Number, optional: true },
        onConfirm: { type: Function, optional: true },
        onDiscard: { type: Function, optional: true },
        close: { type: Function, optional: true },
    };

    static defaultProps = {
        showSeconds: false,
        minutesRounding: 1,
        onConfirm: () => {},
        onDiscard: () => {},
    };

    setup() {
        this.bottomSheetService = useService("bottomSheet");

        // Initial state based on provided value or defaults
        const value = this.props.value || new Time();
        this.state = useState({
            hour: value.hour,
            minute: value.minute,
            second: value.second,
        });

        // Cell height for calculations (in pixels)
        this.cellHeight = 48;

        // References for the scroll containers
        this.hourRef = useRef("hourRef");
        this.minuteRef = useRef("minuteRef");
        this.secondRef = useRef("secondRef");

        // Column configurations - centralize the column definitions
        this.columns = [
            { ref: this.hourRef, values: () => this.hours, stateKey: 'hour' },
            { ref: this.minuteRef, values: () => this.minutes, stateKey: 'minute' },
            { ref: this.secondRef, values: () => this.seconds, stateKey: 'second',
              conditional: () => this.props.showSeconds }
        ];

        // Create a single debounced handler for scroll events
        this.updateFromScroll = useDebounced(this.detectCenteredValue.bind(this), 10);

        onMounted(() => {
            this.scrollToInitialPositions();
            this.setupScrollListeners();
        });
    }

    /**
     * Get the list of hours (0-23)
     * @returns {number[]}
     */
    get hours() {
        return [...Array(24).keys()];
    }

    /**
     * Get the list of minutes, filtered by rounding if needed
     * @returns {number[]}
     */
    get minutes() {
        const minutes = [...Array(60).keys()];
        if (this.props.minutesRounding > 1) {
            return minutes.filter(m => m % this.props.minutesRounding === 0);
        }
        return minutes;
    }

    /**
     * Get the list of seconds (0-59)
     * @returns {number[]}
     */
    get seconds() {
        return [...Array(60).keys()];
    }

    /**
     * Format number as two digits
     * @param {number} num
     * @returns {string}
     */
    formatTwoDigits(num) {
        return num.toString().padStart(2, '0');
    }

    /**
     * Scroll each column to the initial values with smooth snap
     */
    scrollToInitialPositions() {
        // Process each column using the configurations
        for (const column of this.columns) {
            // Skip if column is conditional and condition is false
            if (column.conditional && !column.conditional()) continue;

            // Skip if ref doesn't exist
            if (!column.ref.el) continue;

            const values = column.values();
            const stateValue = this.state[column.stateKey];
            const valueIndex = values.indexOf(stateValue);

            if (valueIndex !== -1) {
                // Set initial scroll position
                column.ref.el.scrollTop = valueIndex * this.cellHeight;

                // Use setTimeout to ensure smooth scrolling after initial render
                setTimeout(() => {
                    column.ref.el.scrollTo({
                        top: valueIndex * this.cellHeight,
                        behavior: 'smooth'
                    });
                }, 50);
            }
        }
    }

    /**
     * Set up scroll event listeners for all columns
     */
    setupScrollListeners() {
        // Add scroll event listeners to each column
        for (const column of this.columns) {
            // Skip if column is conditional and condition is false
            if (column.conditional && !column.conditional()) continue;

            // Skip if ref doesn't exist
            if (!column.ref.el) continue;

            // Add the event listener
            column.ref.el.addEventListener('scroll', () => {
                this.updateFromScroll(column);
            });
        }
    }

    /**
     * Generic method to detect which value is centered in any column
     * @param {Object} column The column configuration object
     */
    detectCenteredValue(column) {
        if (!column.ref.el) return;

        const scrollTop = column.ref.el.scrollTop;
        const centeredIndex = Math.round(scrollTop / this.cellHeight);
        const values = column.values();

        if (centeredIndex >= 0 && centeredIndex < values.length) {
            this.state[column.stateKey] = values[centeredIndex];
        }
    }

    /**
     * Checks if a cell is the one immediately preceding the selected value
     * @param {number} value The current cell value
     * @param {number} selectedValue The selected value in state
     * @param {number[]} allValues All possible values for this column
     * @returns {boolean} True if this cell is the one preceding the selected cell
     */
    isPrecedingCell(value, selectedValue, allValues) {
        const selectedIndex = allValues.indexOf(selectedValue);
        const currentIndex = allValues.indexOf(value);
        return selectedIndex > 0 && currentIndex === selectedIndex - 1;
    }

    /**
     * Apply selected time and close the bottom sheet
     */
    confirmSelection() {
        const value = new Time({
            hour: this.state.hour,
            minute: this.state.minute,
            second: this.state.second,
        });
        this.props.onConfirm(value);
        this.closeSheet();
    }

    /**
     * Close the bottom sheet without applying changes
     */
    discardSelection() {
        this.props.onDiscard();
        this.closeSheet();
    }

    /**
     * Helper method to close the sheet using the appropriate method
     */
    closeSheet() {
        if (this.props.id !== undefined) {
            this.bottomSheetService.remove(this.props.id);
        } else if (this.props.close) {
            this.props.close();
        }
    }
}
