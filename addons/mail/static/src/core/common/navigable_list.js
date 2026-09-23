// @ts-check
/** @odoo-module native */
import { ImStatus } from "@mail/core/common/im_status";
import { onExternalClick } from "@mail/utils/common/hooks";
import { navigateIndex } from "@mail/utils/common/misc";
import { Component, useEffect, useExternalListener, useRef, useState } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { getActiveHotkey } from "@web/core/browser/hotkeys";
import { makeLogger } from "@web/core/debug/debug_logger";
import { usePosition } from "@web/core/position/position_hook";
import { delay } from "@web/core/utils/concurrency";
import { isEventHandled, markEventHandled } from "@web/core/utils/dom/events";
import { useService } from "@web/core/utils/hooks";

const log = makeLogger("mail.navigable_list");
export class NavigableList extends Component {
    static components = { ImStatus };
    static template = "mail.NavigableList";
    static props = {
        anchorRef: { optional: true },
        class: { type: String, optional: true },
        onSelect: { type: Function },
        options: { type: Array },
        optionTemplate: { type: String, optional: true },
        position: { type: String, optional: true },
        closeOnSelect: { type: Boolean, optional: true },
        isLoading: { type: Boolean, optional: true },
    };
    static defaultProps = {
        position: "bottom",
        closeOnSelect: true,
        isLoading: false,
    };

    setup() {
        super.setup();
        this.rootRef = useRef("root");
        this.state = useState({
            activeIndex: null,
            open: false,
            showLoading: false,
        });
        this.hotkey = useService("hotkey");
        this.hotkeysToRemove = [];
        /** @type {Object[]} */
        this.sortedOptions = [];
        /** @type {Map<Object, string>} */
        this.optionKeys = new Map();

        useExternalListener(window, "keydown", this.onKeydown, true);
        onExternalClick(
            "root",
            /** @param {MouseEvent} ev */ async (ev) => {
                await delay();
                if (isEventHandled(ev, "composer.onClickTextarea")) {
                    return;
                }
                this.close();
            },
        );
        const positioning = usePosition("root", () => this.props.anchorRef, {
            position: this.props.position,
        });
        // the root stays in the DOM while closed; do not measure and place it then
        useEffect(
            (show) => (show ? positioning.unlock() : positioning.lock()),
            () => [this.show],
        );
        useEffect(
            () => {
                const optionsKey = this.props.options
                    .map((option) => this.getOptionKey(option))
                    .join("\x00");
                if (optionsKey !== this.lastOptionsKey) {
                    this.lastOptionsKey = optionsKey;
                    this.open();
                }
            },
            () => [this.props.options, this.props.isLoading],
        );
        useEffect(
            () => {
                if (!this.props.isLoading) {
                    browser.clearTimeout(this.loadingTimeoutId);
                    this.loadingTimeoutId = undefined;
                    this.state.showLoading = false;
                } else if (!this.loadingTimeoutId) {
                    this.loadingTimeoutId = browser.setTimeout(
                        () => (this.state.showLoading = true),
                        2000,
                    );
                }
                return () => browser.clearTimeout(this.loadingTimeoutId);
            },
            () => [this.props.isLoading],
        );
    }

    get show() {
        return Boolean(
            this.state.open && (this.props.isLoading || this.props.options.length),
        );
    }

    /**
     * The options in display order and their keys, as the render shows them;
     * the event handlers read the last rendered order.
     *
     * @returns {Object[]}
     */
    sortOptions() {
        this.sortedOptions = [...this.props.options].sort(
            /**
             * @param {Object} o1
             * @param {Object} o2
             */
            (o1, o2) => (o1.group ?? 0) - (o2.group ?? 0),
        );
        this.optionKeys = new Map();
        const usedKeys = new Set();
        for (const option of this.sortedOptions) {
            let key = this.getOptionKey(option);
            while (usedKeys.has(key)) {
                key += "_";
            }
            usedKeys.add(key);
            this.optionKeys.set(option, key);
        }
        return this.sortedOptions;
    }

    /**
     * @param {Object} option
     * @returns {string}
     */
    getOptionKey(option) {
        const record =
            option.partner ?? option.role ?? option.thread ?? option.cannedResponse;
        return `${record?.id ?? option.emoji?.codepoints ?? ""}-${option.label}`;
    }

    open() {
        log.lifecycle("open", () => ({ options: this.props.options.length }));
        this.state.open = true;
        this.state.activeIndex = null;
        this.navigate("first");
    }

    /** @param {boolean} [force] */
    close(force = false) {
        if (force || this.props.closeOnSelect) {
            log.lifecycle("close", () => ({ force }));
            this.state.open = false;
            this.state.activeIndex = null;
        }
    }

    /**
     * @param {Event} ev
     * @param {number} index
     * @param {Object} [params={}]
     */
    selectOption(ev, index, params = {}) {
        const option = this.sortedOptions[index];
        if (!option) {
            return;
        }
        if (option.unselectable) {
            this.close();
            return;
        }
        log.logic("selectOption", () => ({ index, label: option.label }));
        this.props.onSelect(ev, option, {
            ...params,
        });
        this.close();
    }

    /** @param {"first"|"last"|"previous"|"next"} direction */
    navigate(direction) {
        const targetId = navigateIndex(
            direction,
            this.state.activeIndex,
            this.props.options.length,
        );
        if (targetId !== undefined) {
            this.state.activeIndex = targetId;
        }
    }

    /** @param {KeyboardEvent} ev */
    onKeydown(ev) {
        if (!this.show) {
            return;
        }
        const hotkey = getActiveHotkey(ev);
        switch (hotkey) {
            case "enter":
                markEventHandled(ev, "NavigableList.select");
                if (this.state.activeIndex === null) {
                    this.close();
                    return;
                }
                this.selectOption(ev, this.state.activeIndex);
                break;
            case "escape":
                markEventHandled(ev, "NavigableList.close");
                this.close(true);
                break;
            case "tab":
                this.navigate(this.state.activeIndex === null ? "first" : "next");
                break;
            case "arrowup":
                this.navigate(this.state.activeIndex === null ? "first" : "previous");
                break;
            case "arrowdown":
                this.navigate(this.state.activeIndex === null ? "first" : "next");
                break;
            default:
                return;
        }
        if (this.props.options.length !== 0) {
            ev.stopPropagation();
        }
        ev.preventDefault();
    }

    /** @param {number} index */
    onOptionMouseEnter(index) {
        this.state.activeIndex = index;
    }
}
