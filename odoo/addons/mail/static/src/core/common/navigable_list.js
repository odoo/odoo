/* @odoo-module */

import { ImStatus } from "@mail/core/common/im_status";
import { onExternalClick } from "@mail/utils/common/hooks";
import { markEventHandled, isEventHandled } from "@web/core/utils/misc";

import { Component, useEffect, useExternalListener, useRef, useState } from "@odoo/owl";

import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";
import { usePosition } from "@web/core/position_hook";
import { useService } from "@web/core/utils/hooks";

export class NavigableList extends Component {
    static components = { ImStatus };
    static template = "mail.NavigableList";
    static props = {
        anchorRef: { optional: true },
        class: { type: String, optional: true },
        onSelect: { type: Function },
        options: { type: Array },
        optionTemplate: { type: String, optional: true },
        placeholder: { type: String, optional: true },
        position: { type: String, optional: true },
        isLoading: { type: Boolean, optional: true },
    };
    static defaultProps = { position: "bottom", isLoading: false };

    setup() {
        this.rootRef = useRef("root");
        this.state = useState({
            activeIndex: null,
            open: false,
        });
        this.hotkey = useService("hotkey");
        this.hotkeysToRemove = [];

        useExternalListener(window, "keydown", this.onKeydown, true);
        onExternalClick("root", async (ev) => {
            // Let event be handled by bubbling handlers first.
            await new Promise(setTimeout);
            if (
                isEventHandled(ev, "composer.onClickTextarea") ||
                isEventHandled(ev, "channelSelector.onClickInput")
            ) {
                return;
            }
            this.close();
        });
        // position and size
        usePosition("root", () => this.props.anchorRef, { position: this.props.position });
        useEffect(
            () => {
                this.open();
            },
            () => [this.props]
        );
    }

    get show() {
        return Boolean(this.state.open && (this.props.isLoading || this.props.options.length));
    }

    open() {
        this.state.open = true;
        this.state.activeIndex = null;
        this.navigate("first");
    }

    close() {
        this.state.open = false;
        this.state.activeIndex = null;
    }

    selectOption(ev, index, params = {}) {
        const option = this.props.options[index];
        if (option.unselectable) {
            this.close();
            return;
        }
        this.props.onSelect(ev, option, {
            ...params,
        });
        this.close();
    }

    navigate(direction) {
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
                if (!this.show || this.state.activeIndex === null) {
                    return;
                }
                markEventHandled(ev, "NavigableList.select");
                this.selectOption(ev, this.state.activeIndex);
                break;
            case "escape":
                markEventHandled(ev, "NavigableList.close");
                this.close();
                break;
            case "tab":
                this.navigate("next");
                break;
            case "arrowup":
                this.navigate("previous");
                break;
            case "arrowdown":
                this.navigate("next");
                break;
            default:
                return;
        }
        ev.preventDefault();
    }

    onOptionMouseEnter(index) {
        this.state.activeIndex = index;
    }
}
