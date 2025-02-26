import { Component, useState, useRef, onWillUpdateProps } from "@odoo/owl";
import { Time, parseTime } from "@web/core/l10n/time";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";
import { useChildRef } from "@web/core/utils/hooks";

const HOURS = [...Array(24)].map((_, i) => i);
const MINUTES = [...Array(60)].map((_, i) => i);

/**
* @typedef TimePickerProps
* @property {string} [class=""]
* @property {string|Time} [value]
* @property {(value: Time) => any} [onChange]
* @property {boolean} [showSeconds=false]
* @property {number} [minutesRounding=5]
*/

export class TimePicker extends Component {
    static template = "web.TimePicker";
    static components = {
        Dropdown,
        DropdownItem,
    };
    static props = {
        class: { type: String, optional: true },
        value: { type: [String, Time], optional: true },
        onChange: { type: Function, optional: true },
        showSeconds: { type: Boolean, optional: true },
        minutesRounding: { type: Number, optional: true },
    };
    static defaultProps = {
        class: "",
        onChange: () => {},
        showSeconds: false,
        minutesRounding: 5,
    };

    setup() {
        this.inputRef = useRef("inputRef");
        this.menuRef = useChildRef();
        this.dropdownState = useDropdownState();

        this.state = useState({
            value: new Time(),
            inputValue: "",
            isValid: true,
        });

        /**@type {Time[]}*/
        this.suggestions = [];
        this.isNavigating = false;
        this.navigationOptions = this.getNavigationOptions();
        this.onPropsUpdated(this.props);

        onWillUpdateProps((nextProps) => this.onPropsUpdated(nextProps));
    }

    /**
     * @returns {import("@web/core/navigation/navigation").NavigationOptions}
     */
    getNavigationOptions() {
        const handleArrow = (navigator) => {
            const value = this.suggestions[navigator.activeItemIndex];
            if (value) {
                this.state.inputValue = value.toString(this.props.showSeconds);
            }
        };

        return {
            virtualFocus: true,
            focusInitialElementOnDisabled: () => false,
            onEnabled: (navigator) => {
                this.navigator = navigator;
                if (this.state.value) {
                    const index = this.suggestions.findIndex((s) => s.equals(this.state.value, this.props.showSeconds));
                    if (index >= 0) {
                        navigator.items[index]?.setActive();
                    }
                }
            },
            hotkeys: {
                enter: {
                    bypassEditableProtection: true,
                    callback: (navigator) => {
                        if (!this.isNavigating) {
                            const value = parseTime(this.inputRef.el.value, this.props.showSeconds);
                            if (value) {
                                this.setValue(value);
                                this.close();
                            }
                        } else if (navigator.activeItem) {
                            navigator.activeItem.select();
                        }
                    },
                },
                tab: {
                    bypassEditableProtection: true,
                    callback: (navigator) => {
                        if (navigator.activeItemIndex >= 0) {
                            this.setValue(this.suggestions[navigator.activeItemIndex]);
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

    /**
     * @param {TimePickerProps} props
     */
    onPropsUpdated(props) {
        if (this.suggestions.length === 0) {
            this.suggestions = this.getSuggestions(props);
        }

        const newValue = Time.from(props.value);
        if (!newValue.equals(this.lastPropsValue, this.props.showSeconds)) {
            this.lastPropsValue = newValue;
            this.lastValue = newValue; // Prevents triggering props.onChange
            this.setValue(newValue, false);
        }
    }

    /**
     * @param {TimePickerProps} props
     * @returns {Time[]}
     */
    getSuggestions(props) {
        const suggestions = [];
        const rounding = props.minutesRounding <= 5 ? 15 : props.minutesRounding;
        const minutes = MINUTES.filter((m) => !(m % rounding));
        for (const hour of HOURS) {
            for (const minute of minutes) {
                suggestions.push(new Time({ hour, minute }));
            }
        }
        return suggestions;
    }

    /**
     * @param {Time} newValue
     * @param {boolean} [cleanValue=true]
     */
    setValue(newValue, cleanValue = true) {
        if (cleanValue) {
            if (this.props.minutesRounding > 1) {
                newValue.roundMinutes(this.props.minutesRounding);
            }
            // If showSeconds is false, keep the seconds from
            // the original props.value
            if (!this.props.showSeconds && this.state.value) {
                newValue.second = this.state.value.second;
            }
        }

        this.state.value = newValue;
        this.state.inputValue = newValue.toString(this.props.showSeconds);
        this.state.isValid = true;

        if (!newValue.equals(this.lastValue, this.props.showSeconds)) {
            this.lastValue = newValue.copy();
            this.props.onChange(newValue.copy());
        }
    }

    /**
     * @param {Time} value
     */
    onItemSelected(value) {
        this.setValue(value);
        this.close();
    }

    /**
     * @param {InputEvent} event
     */
    onInput(event) {
        this.ensureOpen();

        const value = parseTime(this.inputRef.el.value, this.props.showSeconds);
        this.state.isValid = value !== null;

        if (!this.navigator) {
            return;
        }

        let index = -1;
        if (this.state.isValid) {
            index = this.suggestions.findIndex((s) => s.equals(value));
        }

        if (index === -1) {
            this.navigator.activeItem?.setInactive();
        } else {
            this.navigator.items[index]?.setActive();
        }
    }

    onChange() {
        const value = parseTime(this.inputRef.el.value, this.props.showSeconds);
        this.state.isValid = value !== null;
        if (this.state.isValid) {
            this.setValue(value);
            this.close();
        }
    }

    /**
     * @param {KeyboardEvent} event
     */
    onKeydown(event) {
        this.isNavigating = ["arrowup", "arrowdown"].includes(getActiveHotkey(event));
    }

    ensureOpen() {
        if (!this.dropdownState.isOpen) {
            this.isNavigating = false;
            this.dropdownState.open();
            this.inputRef.el.select();
        }
    }

    close() {
        this.dropdownState.close();
    }

    /**
     * @returns {string}
     */
    getPlaceholder() {
        const seconds = this.props.showSeconds ? ":ss" : "";
        return `hh:mm${seconds}`;
    }
}
