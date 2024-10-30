import { Component, useState, useRef, useEffect } from "@odoo/owl";

export class EditListInput extends Component {
    static template = "point_of_sale.EditListInput";
    static props = {
        item: Object,
        deletable: Boolean,
        createNewItem: Function,
        onInputChange: Function,
        removeItem: Function,
        getOptions: Function,
        shouldShowOptions: Boolean,
        hasInvalidValue: Boolean,
        customInput: Boolean,
        onSelectItem: Function,
        onUnselectItem: Function,
    };

    setup() {
        super.setup();
        this.state = useState({
            selectedOptionValue: null,
            hideOptions: false,
        });
        const optionsDropdownRef = useRef("options-dropdown");
        useEffect(
            (el) => {
                this.setupOptionsDropdown(el);
            },
            () => [optionsDropdownRef.el]
        );
    }
    get displayedOptions() {
        const options = this.props.getOptions();
        if (!this.props.customInput || this.props.hasInvalidValue) {
            return options;
        }
        return options.filter((o) => o.includes(this.props.item.text));
    }
    onKeyup(event) {
        if (event.key === "Enter") {
            if (this.state.selectedOptionValue) {
                this.onSelectOption(this.state.selectedOptionValue);
            } else if (event.target.value.trim() !== "") {
                this.props.createNewItem();
            }
        }
    }
    onKeydown(event) {
        let optionSelectionRelativeMove = 0;
        if (event.key === "ArrowDown") {
            optionSelectionRelativeMove = 1;
        } else if (event.key === "ArrowUp") {
            optionSelectionRelativeMove = -1;
        }

        if (optionSelectionRelativeMove !== 0) {
            event.preventDefault();
            if (this.displayedOptions && this.displayedOptions.length > 0) {
                const curSelectedOptionValue = this.state.selectedOptionValue;
                const curSelectedOptionIndex = curSelectedOptionValue
                    ? this.displayedOptions.findIndex((o) => o === curSelectedOptionValue)
                    : null;
                let nextSelectedOptionIndex;
                if (curSelectedOptionIndex !== null) {
                    nextSelectedOptionIndex =
                        (curSelectedOptionIndex + optionSelectionRelativeMove) %
                        this.displayedOptions.length;
                    if (nextSelectedOptionIndex < 0) {
                        nextSelectedOptionIndex = this.displayedOptions.length - 1;
                    }
                } else {
                    nextSelectedOptionIndex = 0;
                }
                this.state.selectedOptionValue = this.displayedOptions[nextSelectedOptionIndex];
                const optionsEl = document.querySelectorAll(".options-dropdown .option");
                if (optionsEl?.length > nextSelectedOptionIndex) {
                    const nextSelectedOptionEl = optionsEl[nextSelectedOptionIndex];
                    if (nextSelectedOptionEl) {
                        nextSelectedOptionEl.scrollIntoView({
                            behavior: "smooth",
                            block: "center",
                        });
                    }
                }
            }
        }
    }
    onClick(event) {
        this.resetOptionsDropdown();
    }
    onInput(event) {
        this.props.onInputChange(this.props.item._id, event.target.value);
        this.resetOptionsDropdown();
    }
    onFocus(event) {
        this.props.onSelectItem(this.props.item._id);
        this.resetOptionsDropdown();
    }
    setupOptionsDropdown(optionsDropdownEl) {
        const inputEl = optionsDropdownEl?.parentElement;
        if (!inputEl) {
            return;
        }
        const inputRect = inputEl.getBoundingClientRect();

        optionsDropdownEl.style.left = inputRect.left + "px";
        optionsDropdownEl.style.top = inputRect.top + inputRect.height + "px";
        optionsDropdownEl.style.width = inputRect.width + "px";
    }
    resetOptionsDropdown() {
        if (this.state.hideOptions) {
            this.state.hideOptions = false;
        }
        this.state.selectedOptionValue = null;
    }
    onBlur(event) {
        this.props.onUnselectItem(this.props.item._id);
        this.state.selectedOptionValue = null;
    }
    onSelectOption(optionValue) {
        this.props.onInputChange(this.props.item._id, optionValue);
        this.state.selectedOptionValue = null;
        this.state.hideOptions = !this.props.customInput;
    }
}
