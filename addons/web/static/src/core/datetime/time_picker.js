import { Component, useState, useRef, onWillUpdateProps } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";
import { parseTime, is24HourFormat, isMeridiemFormat } from "@web/core/l10n/dates";
import { useChildRef } from "@web/core/utils/hooks";

const { DateTime } = luxon;

const HOURS = [...Array(24)].map((_, i) => i);
const MINUTES = [...Array(60)].map((_, i) => i);

/**
 * @param {import("luxon").DateTimeMaybeValid} time
 */
function copyTime(time) {
    return DateTime.fromObject({
        hour: time.hour,
        minute: time.minute,
        second: time.second,
    });
}

function roundMinute(value, rounding) {
    const minute = Math.round(value.minute / rounding) * rounding;
    return value.set({ minute });
}

export class TimePicker extends Component {
    static template = "web.TimePicker";
    static components = {
        Dropdown,
        DropdownItem,
    };
    static props = {
        class: { type: [String, Object], optional: true },
        value: { type: Object, optional: true },
        onChange: { type: Function, optional: true },
        showSeconds: { type: Boolean, optional: true },
        minutesRounding: { type: Number, optional: true },
    };
    static defaultProps = {
        value: DateTime.fromObject({ hour: 0, minute: 0, second: 0 }),
        onChange: () => {},
        showSeconds: false,
        minutesRounding: 5,
    };

    setup() {
        this.inputRef = useRef("inputRef");
        this.menuRef = useChildRef();
        this.dropdownState = useDropdownState();

        this.state = useState({
            value: undefined,
            inputValue: undefined,
            suggestions: [],
            isValid: true,
        });

        this.is12HourFormat = !is24HourFormat();
        this.isMeridiemFormat = isMeridiemFormat();

        this.canOpen = true;
        this.isNavigating = false;
        this.lastValue = undefined;
        this.lastPropsValue = undefined;
        this.lastMinutesRounding = undefined;
        this.navigator = undefined;

        this.navigationOptions = this.getNavigationOptions();

        this.onPropsUpdated(this.props);
        onWillUpdateProps((nextProps) => this.onPropsUpdated(nextProps));
    }

    /**
     * @return {import("@web/core/navigation/navigation").NavigationOptions}
     */
    getNavigationOptions() {
        const handleArrow = (navigator) => {
            const value = this.state.suggestions[navigator.activeItemIndex];
            if (value) {
                this.state.inputValue = this.timeToString(value);
            }
        };

        return {
            virtualFocus: true,
            onEnabled: (navigator) => {
                this.navigator = navigator;
                if (this.state.value) {
                    const index = this.state.suggestions.findIndex((s) =>
                        s.equals(this.state.value)
                    );
                    if (index >= 0) {
                        navigator.items[index]?.setActive();
                    }
                }
            },
            hotkeys: {
                enter: {
                    bypassEditableProtection: true,
                    callback: (navigator) => {
                        if (!this.isNavigating && this.state.isValid) {
                            const value = parseTime(this.inputRef.el.value, this.props.showSeconds);
                            this.setValue(value);
                            this.close();
                        } else if (this.isNavigating && navigator.activeItem) {
                            navigator.activeItem.select();
                        }
                    },
                },
                tab: {
                    bypassEditableProtection: true,
                    callback: (navigator) => {
                        if (navigator.activeItemIndex >= 0) {
                            this.setValue(this.state.suggestions[navigator.activeItemIndex]);
                            this.close();
                        }
                    },
                },
                arrowdown: {
                    callback: (navigator) => {
                        navigator.next();
                        handleArrow(navigator);
                    },
                },
                arrowup: {
                    callback: (navigator) => {
                        navigator.previous();
                        handleArrow(navigator);
                    },
                },
            },
        };
    }

    onPropsUpdated(props) {
        if (props.minutesRounding !== this.lastMinutesRounding) {
            this.state.suggestions = this.getSuggestions(props);
            this.lastMinutesRounding = props.minutesRounding;
        }

        const getTime = (value) => {
            if (typeof value === "string") {
                return parseTime(value, true);
            } else if (value) {
                return value;
            } else {
                return DateTime.fromObject({ hour: 0, minute: 0, second: 0 });
            }
        };

        const newValue = getTime(props.value);
        const lastPropsValue = getTime(this.lastPropsValue);
        if (!newValue.equals(lastPropsValue)) {
            this.lastPropsValue = lastPropsValue;
            this.lastValue = newValue; // Prevents triggering props.onChange
            this.setValue(newValue, false);
        }
    }

    /**
     * @param {*} props
     * @returns {Array<DateTime>}
     */
    getSuggestions(props) {
        const suggestions = [];
        const rounding = props.minutesRounding <= 5 ? 15 : props.minutesRounding;
        const minutes = MINUTES.filter((m) => !(m % rounding));
        for (const hour of HOURS) {
            for (const minute of minutes) {
                suggestions.push(DateTime.fromObject({ hour, minute }));
            }
        }
        return suggestions;
    }

    /**
     * @param {DateTime} value
     */
    setValue(newValue, cleanValue = true) {
        if (cleanValue) {
            if (this.props.minutesRounding > 1) {
                newValue = roundMinute(newValue, this.props.minutesRounding);
            }
            // If showSeconds is false, keep the seconds from
            // the original props.value
            if (!this.props.showSeconds && this.state.value) {
                newValue = newValue.set({ second: this.state.value.second });
            }
        }

        this.state.value = newValue;
        this.state.inputValue = this.timeToString(newValue);
        this.state.isValid = true;

        if (this.lastValue === undefined || !newValue.equals(this.lastValue)) {
            this.lastValue = copyTime(newValue);
            this.props.onChange(copyTime(newValue));
        }
    }

    /**
     * @param {DateTime} value
     */
    onItemSelected(value) {
        this.setValue(value);
        this.close();
    }

    /**
     * @param {InputEvent} event
     */
    onInput(event) {
        event.preventDefault();
        this.ensureOpen();

        const strValue = this.inputRef.el.value.replace(/[^0-9:AaMmPp ]/g, "");
        this.inputRef.el.value = strValue;

        const value = parseTime(strValue, this.props.showSeconds);
        this.state.isValid = value !== null;

        if (!this.navigator) {
            return;
        }

        let index = -1;
        if (this.state.isValid) {
            index = this.state.suggestions.findIndex((s) => s.equals(value));
        }

        if (index === -1) {
            this.navigator.activeItem?.setInactive();
        } else {
            this.navigator.items[index]?.setActive();
        }
    }

    onChange() {
        if (this.state.isValid) {
            const value = parseTime(this.inputRef.el.value, this.props.showSeconds);
            this.setValue(value);
            this.close();
        }
    }

    onKeydown(event) {
        this.isNavigating = ["arrowup", "arrowdown"].includes(getActiveHotkey(event));
    }

    ensureOpen() {
        if (!this.dropdownState.isOpen && this.canOpen) {
            this.isNavigating = false;
            this.dropdownState.open();
            this.inputRef.el.select();
        }
    }

    close() {
        this.canOpen = false;
        this.dropdownState.close();
        setTimeout(() => {
            this.canOpen = true;
        });
    }

    /**
     * @param {DateTime} time
     * @param {boolean} hideSeconds
     */
    timeToString(time, hideSeconds = false) {
        if (!time) {
            time = DateTime.fromObject({ hour: 0, minute: 0, second: 0 });
        }
        return time.toFormat(this.getFormat(hideSeconds)).toLowerCase();
    }

    /**
     * @param {boolean?} hideSeconds
     */
    getFormat(hideSeconds = false) {
        const hourFormat = this.is12HourFormat ? "h" : "H";
        const secondFormat = !hideSeconds && this.props.showSeconds ? ":ss" : "";
        const meridiemFormat = this.isMeridiemFormat ? "a" : "";
        return `${hourFormat}:mm${secondFormat}${meridiemFormat}`;
    }
}
