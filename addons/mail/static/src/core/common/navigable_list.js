import { useSubEnv } from "@web/owl2/utils";
import { DiscussAvatar } from "@mail/core/common/discuss_avatar";
import { optionType } from "@mail/core/common/suggestion_hook";
import { onExternalClick } from "@mail/utils/common/hooks";
import { markEventHandled, isEventHandled } from "@web/core/utils/misc";

import { Component, proxy, signal, t, useListener, useOnChange, useProps } from "@odoo/owl";

import { getActiveHotkey } from "@web/core/hotkeys/hotkey_utils";
import { usePosition } from "@web/core/position/position_hook";
import { useService } from "@web/core/utils/hooks";

/**
 * Returns a string representation of the options, to tell a new set of options
 * apart from the same set rebuilt at the next render. Every field is taken into
 * account because `label` is optional (an option can be rendered by an
 * arbitrary `optionTemplate`), and records are identified by their local id.
 *
 * @param {Object[]} options
 * @returns {string}
 */
function optionsToString(options) {
    return options
        .map((option) =>
            Object.entries(option)
                .map(([name, value]) => `${name}:${value?.localId ?? value}`)
                .join(",")
        )
        .join("\n");
}

export class NavigableList extends Component {
    static components = { DiscussAvatar };
    static template = "mail.NavigableList";

    rootRef = signal.ref();

    setup() {
        super.setup();
        this.store = useService("mail.store");
        const option = optionType(this.store);
        this.props = useProps({
            anchorRef: t.signal(t.instanceOf(HTMLElement)).optional(),
            class: t.string().optional(),
            closeOnSelect: t.boolean().optional(true),
            isLoading: t.boolean().optional(false),
            onSelect: t.function([t.instanceOf(Event), option]),
            options: t.array(option),
            optionTemplate: t.string().optional(),
            position: t.string().optional("bottom"),
            rememberPosition: t.boolean().optional(),
        });
        useSubEnv({ inNavigableList: true });
        this.state = proxy({
            activeIndex: null,
            open: false,
            showLoading: false,
        });
        this.hotkey = useService("hotkey");
        this.hotkeysToRemove = [];
        useListener(this.env.pipWindow || window, "keydown", (ev) => this.onKeydown(ev), true);
        onExternalClick(this.rootRef, async (ev) => {
            // Let event be handled by bubbling handlers first.
            await new Promise(setTimeout);
            if (isEventHandled(ev, "composer.onClickTextarea")) {
                return;
            }
            this.close();
        });
        // position and size
        usePosition(this.rootRef, () => this.props.anchorRef?.(), {
            position: this.props.position,
            rememberPosition: this.props.rememberPosition,
        });
        useOnChange(
            // Open on mount and when a new set of options arrives. In particular,
            // do not re-open on unrelated re-renders after the user closed the
            // list (Escape, click away): the options are then the same.
            () => [optionsToString(this.props.options)],
            () => this.open()
        );
        useOnChange(
            () => [this.props.isLoading],
            (isLoading) => {
                if (isLoading) {
                    const loadingTimeoutId = setTimeout(
                        () => (this.state.showLoading = true),
                        2000
                    );
                    return () => {
                        clearTimeout(loadingTimeoutId);
                        this.state.showLoading = false;
                    };
                }
            }
        );
    }

    get show() {
        return Boolean(this.state.open && (this.props.isLoading || this.props.options.length));
    }

    get sortedOptions() {
        return this.props.options.sort((o1, o2) => (o1.group ?? 0) - (o2.group ?? 0));
    }

    open() {
        this.state.open = true;
        this.state.activeIndex = null;
        this.navigate("first");
    }

    close() {
        if (this.props.closeOnSelect) {
            this.state.open = false;
            this.state.activeIndex = null;
        }
    }

    /**
     * @param {Event} ev
     * @param {import("@mail/core/common/suggestion_hook").Option} option
     */
    selectOption(ev, option) {
        if (!option) {
            return;
        }
        if (option.unselectable) {
            this.close();
            return;
        }
        this.props.onSelect(ev, option);
        this.close();
    }

    navigate(direction) {
        if (this.props.options.length === 0) {
            return;
        }
        const activeOptionId = this.state.activeIndex !== null ? this.state.activeIndex : 0;
        let targetId = undefined;
        switch (direction) {
            case "first":
                targetId = 0;
                break;
            case "last":
                targetId = this.props.options.length - 1;
                break;
            case "previous":
                targetId = activeOptionId - 1;
                if (targetId < 0) {
                    this.navigate("last");
                    return;
                }
                break;
            case "next":
                targetId = activeOptionId + 1;
                if (targetId > this.props.options.length - 1) {
                    this.navigate("first");
                    return;
                }
                break;
            default:
                return;
        }
        this.state.activeIndex = targetId;
    }

    onKeydown(ev) {
        if (!this.show) {
            return;
        }
        const hotkey = getActiveHotkey(ev);
        switch (hotkey) {
            case "enter":
                if (this.state.activeIndex === null) {
                    // Nothing is selectable (e.g. list is open but still loading
                    // with no options yet). Let Enter propagate so the composer
                    // can send the message instead of being swallowed.
                    this.close();
                    return;
                }
                markEventHandled(ev, "NavigableList.select");
                this.selectOption(ev, this.props.options[this.state.activeIndex]);
                break;
            case "escape":
                markEventHandled(ev, "NavigableList.close");
                this.close();
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

    onOptionMouseEnter(index) {}
}
