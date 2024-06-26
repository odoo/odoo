import { Component, useExternalListener, useState } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { isEventHandled } from "@web/core/utils/misc";
import { usePopover } from "@web/core/popover/popover_hook";
import { useService } from "@web/core/utils/hooks";
import { PickerContent } from "@mail/core/common/picker_content";
import { useLazyExternalListener } from "@mail/utils/common/hooks";

export function usePicker(setting) {
    const storeScroll = {
        scrollValue: 0,
        set: (value) => (storeScroll.scrollValue = value),
        get: () => storeScroll.scrollValue,
    };
    const PICKERS = {
        NONE: "none",
        EMOJI: "emoji",
        GIF: "gif",
    };
    return useState({
        PICKERS,
        anchor: setting.anchor,
        buttons: setting.buttons,
        close: setting.close,
        pickers: setting.pickers,
        position: setting.position,
        inChatter: setting.inChatter,
        state: {
            picker: PICKERS.NONE,
            searchTerm: "",
        },
        storeScroll,
    });
}

/**
 * Picker/usePicker is a component hook that can be used to display the emoji picker/gif picker (if it is enabled).
 * It can be used in two ways:
 * - with a popover when in large screen: the picker will be displayed in a popover triggered by provided buttons.
 * - with a keyboard when in mobile view: the picker will be displayed in place where the Picker component is placed.
 * The switch between the two modes is done automatically based on the screen size.
 */

export class Picker extends Component {
    static components = {
        PickerContent,
    };
    static props = [
        "PICKERS",
        "anchor?",
        "buttons",
        "close?",
        "inChatter?",
        "state",
        "pickers",
        "position?",
        "storeScroll",
    ];
    static template = "mail.Picker";

    setup() {
        this.ui = useState(useService("ui"));
        this.popover = usePopover(PickerContent, {
            position: this.props.position,
            popoverClass: this.ui.isSmall ? "o-mail-small-emoji-picker" : "",
            fixedPosition: true,
            onClose: () => this.close(),
            closeOnClickAway: false,
            animation: false,
            arrow: false,
        });
        useExternalListener(
            browser,
            "click",
            async (ev) => {
                if (this.props.state.picker === this.props.PICKERS.NONE) {
                    return;
                }
                await new Promise(setTimeout); // let bubbling to catch marked event handled
                if (!this.isEventHandledByPicker(ev)) {
                    this.close();
                }
            },
            true
        );
        for (const button of this.props.buttons) {
            useLazyExternalListener(
                () => button.el,
                "click",
                async (ev) => this.toggle(this.props.anchor?.el ?? button.el, ev)
            );
        }
    }

    get contentProps() {
        const pickers = {};
        for (const [name, fn] of Object.entries(this.props.pickers)) {
            pickers[name] = (str, resetOnSelect) => {
                fn(str);
                if (resetOnSelect) {
                    this.close();
                }
            };
        }
        return {
            PICKERS: this.props.PICKERS,
            close: () => this.close(),
            pickers,
            state: this.props.state,
            storeScroll: this.props.storeScroll,
        };
    }

    /**
     * @param {Event} ev
     * @returns {boolean}
     */
    isEventHandledByPicker(ev) {
        return (
            isEventHandled(ev, "Composer.onClickAddEmoji") ||
            isEventHandled(ev, "PickerContent.onClick")
        );
    }

    async toggle(el, ev) {
        // Let event be handled by bubbling handlers first.
        await new Promise(setTimeout);
        // When screen is small and picker is not in the chatter, we toggle keyboard picker.
        if (this.ui.isSmall && !this.props.inChatter) {
            if (this.props.state.picker === this.props.PICKERS.NONE) {
                this.props.state.picker = this.props.PICKERS.EMOJI;
            } else {
                this.props.state.picker = this.props.PICKERS.NONE;
            }
            return;
        }
        // When screen is large or picker is inside the chatter, we toggle popover.
        if (isEventHandled(ev, "Composer.onClickAddEmoji")) {
            if (this.popover.isOpen) {
                if (this.props.state.picker === this.props.PICKERS.EMOJI) {
                    this.props.state.picker = this.props.PICKERS.NONE;
                    this.popover.close();
                    this.ui.isSmall &&
                        this.env.bus.trigger("toggle_padding_emoji_picker", { addPadding: false });
                    return;
                }
                this.props.state.picker = this.props.PICKERS.EMOJI;
            } else {
                this.props.state.picker = this.props.PICKERS.EMOJI;
                this.ui.isSmall &&
                    this.env.bus.trigger("toggle_padding_emoji_picker", { addPadding: true });
                this.popover.open(el, this.contentProps);
            }
        }
    }

    close() {
        this.props.close?.();
        this.ui.isSmall &&
            this.props.inChatter &&
            this.env.bus.trigger("toggle_padding_emoji_picker", { addPadding: false });
        this.popover.close();
        this.props.state.picker = this.props.PICKERS.NONE;
        this.props.state.searchTerm = "";
    }
}
