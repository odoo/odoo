import { registry } from "@web/core/registry";
import { EmojiPicker } from "@web/core/emoji_picker/emoji_picker";
import { useService } from "@web/core/utils/hooks";
import { onMounted, useEffect, useState, onWillPatch, onPatched } from "@odoo/owl";
import { loadBundle } from "@web/core/assets";
import { usePopover } from "@web/core/popover/popover_hook";
import { onExternalClick } from "@mail/utils/common/hooks";

/**
 *
 * @param {import("@web/core/utils/hooks").Ref} [ref]
 * @param {Object} props
 * @param {import("@web/core/popover/popover_service").PopoverServiceAddOptions} [options]
 * @param {function} [props.onSelect]
 * @param {function} [props.onClose]
 */
export function useEmojiPickerMobile(ref, props, options = {}) {
    const main_components_registry = registry.category("main_components");
    const emojiPickerMobileExists = main_components_registry.content["mail.EmojiPickerMobile"];
    if (!emojiPickerMobileExists) {
        main_components_registry.add("mail.EmojiPickerMobile", { Component: EmojiPickerMobile });
    }
    const targets = [];
    const state = useState({ isOpen: false });
    const newOptions = {
        ...options,
        onClose: () => {
            state.isOpen = false;
            options.onClose?.();
        },
    };
    const store = useService("mail.store");
    let popover;
    const ui = useService("ui");
    const originalOnSelect = props.onSelect;
    if (!ui.isSmall) {
        popover = usePopover(EmojiPicker, { ...newOptions, animation: false });
    }

    function onSelectExtension(...args) {
        originalOnSelect(...args);
        if (props?.resetOnSelect) {
            store.emoji_picker_mobile.isVisible = false;
        }
    }

    props.onSelect = onSelectExtension;
    props.storeScroll = {
        scrollValue: 0,
        set: (value) => {
            props.storeScroll.scrollValue = value;
        },
        get: () => {
            return props.storeScroll.scrollValue;
        },
    };
    store.emoji_picker_mobile = {
        isVisible: store.emoji_picker_mobile.isVisible,
        props: { ...props },
    };

    /**
     * @param {import("@web/core/utils/hooks").Ref} ref
     */
    function add(ref, onSelect, { show = false } = {}) {
        const toggler = () => toggle(ref, onSelect);
        targets.push([ref, toggler]);
        if (!ref.el) {
            return;
        }
        ref.el.addEventListener("click", toggler);
        ref.el.addEventListener("mouseenter", loadEmoji);
        if (show) {
            ref.el.click();
        }
    }

    function toggle(ref, onSelect = props.onSelect) {
        if (ui.isSmall) {
            store.emoji_picker_mobile.isVisible = !store.emoji_picker_mobile.isVisible;
        } else {
            if (popover.isOpen) {
                popover.close();
                store.emoji_picker_mobile.isVisible = false;
            } else {
                state.isOpen = true;
                popover.open(ref.el, { ...props, onSelect });
            }
        }
    }

    if (ref) {
        add(ref);
    }
    onMounted(() => {
        for (const [ref, toggle] of targets) {
            if (!ref.el) {
                continue;
            }
            ref.el.addEventListener("click", toggle);
            ref.el.addEventListener("mouseenter", loadEmoji);
        }
    });
    onWillPatch(() => {
        for (const [ref, toggle] of targets) {
            if (!ref.el) {
                continue;
            }
            ref.el.removeEventListener("click", toggle);
            ref.el.removeEventListener("mouseenter", loadEmoji);
        }
    });
    onPatched(() => {
        for (const [ref, toggle] of targets) {
            if (!ref.el) {
                continue;
            }
            ref.el.addEventListener("click", toggle);
            ref.el.addEventListener("mouseenter", loadEmoji);
        }
    });
    Object.assign(state, { add });
    return state;
}

export const loader = {
    loadEmoji: () => loadBundle("web.assets_emoji"),
};

/**
 * @returns {import("@web/core/emoji_picker/emoji_data")}
 */
export async function loadEmoji() {
    try {
        await loader.loadEmoji();
        const { getCategories, getEmojis } = odoo.loader.modules.get(
            "@web/core/emoji_picker/emoji_data"
        );
        return {
            categories: getCategories(),
            emojis: getEmojis(),
        };
    } catch {
        // Could be intentional (tour ended successfully while emoji still loading)
        return { emojis: [], categories: [] };
    }
}
export class EmojiPickerMobile extends EmojiPicker {
    static template = "mail.EmojiPickerMobile";
    setup() {
        super.setup();
        this.store = useState(useService("mail.store"));
        onExternalClick("emojipickermobile", (ev) => {
            ev.stopPropagation();
            this.store.emoji_picker_mobile.isVisible = false;
        });

        useEffect(
            () => {
                if (this.store.emoji_picker_mobile?.props) {
                    this.props = this.store.emoji_picker_mobile.props;
                }
            },
            () => [this.store.emoji_picker_mobile.isVisible]
        );
    }
}
