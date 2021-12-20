/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { debounce } from "@web/core/utils/timing";

const { Component } = owl;
const { useExternalListener, useRef, useState } = owl.hooks;

export class AutoComplete extends Component {
    setup() {
        this.hotkey = useService("hotkey");

        this.state = useState({
            opened: false,
            suggestions: [],
        });

        this.inputRef = useRef("input");
        this.debouncedLoadSuggestions = debounce(
            this.loadSuggestions.bind(this),
            this.constructor.delay
        );

        useExternalListener(window, "click", this.onWindowClick);
        useExternalListener(window, "scroll", this.onWindowScroll, true);

        this.hotkey.add("escape", () => this.toggle(false));
    }

    get nextId() {
        return ++AutoComplete.nextId;
    }
    get isOpened() {
        return this.state.opened;
    }
    toggle(value = null) {
        this.state.opened = value !== null ? value : !this.state.opened;
    }

    async loadSuggestions(request = null) {
        const results = await this.props.fetchSuggestions(
            request !== null ? request : this.inputRef.el.value.trim()
        );
        this.state.suggestions = results.map((result) => ({
            ...result,
            id: this.nextId,
        }));
        this.toggle(true);
    }

    async onSuggestionSelected(suggestion) {
        this.toggle(false);
        if (suggestion.onSelected) {
            await suggestion.onSelected({
                setValue: (value) => {
                    this.inputRef.el.value = value;
                },
            });
        }
    }
    async onInput(ev) {
        if (this.props.onInput) {
            this.props.onInput(ev.target.value);
        }
        await this.debouncedLoadSuggestions();
    }
    onChange(ev) {
        if (this.props.onChange) {
            this.props.onChange(ev.target.value);
        }
    }
    async onInputClick() {
        if (this.isOpened) {
            this.toggle(false);
        } else {
            const value = this.inputRef.el.value.trim();
            await this.loadSuggestions(value !== this.props.value ? value : "");
        }
    }
    onWindowClick(ev) {
        if (!this.state.opened) {
            return;
        }
        if (!this.el.contains(ev.target)) {
            this.toggle(false);
        }
    }
    onWindowScroll(ev) {
        if (this.isOpened) {
            if (!this.el.contains(ev.target)) {
                this.toggle(false);
            }
        }
    }
}
Object.assign(AutoComplete, {
    template: "web.AutoComplete",
    props: {
        value: String,
        fetchSuggestions: Function,
        placeholder: { type: String, optional: true },
        onInput: { type: Function, optional: true },
        onChange: { type: Function, optional: true },
    },

    nextId: 0,
    delay: 200,
});
