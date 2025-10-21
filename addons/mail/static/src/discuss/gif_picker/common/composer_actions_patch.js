import {
    ComposerPicker,
    EMOJI_ACTION_ID,
    registerComposerAction,
} from "@mail/core/common/composer_actions";
import { _t } from "@web/core/l10n/translation";
import { GifPicker } from "./gif_picker";
import { usePopover } from "@web/core/popover/popover_hook";
import { useService } from "@web/core/utils/hooks";
import { ACTION_TAGS } from "@mail/core/common/action";
import { markEventHandled } from "@web/core/utils/misc";

registerComposerAction("add-gif", {
    actionPanelComponent: GifPicker,
    actionPanelName: _t("GIF"),
    actionPanelOpen({ actions, ev, owner }) {
        if (ev) {
            markEventHandled(ev, "Composer.onClickAddGif");
        }
        const pickerActions = actions.actions.filter((act) =>
            act.tags.includes(ACTION_TAGS.COMPOSER_PICKER)
        );
        this.popover?.open(owner.root.el.querySelector(`[name="${EMOJI_ACTION_ID}"]`), {
            pickerActions,
            component: GifPicker,
            componentProps: {
                onSelect: (gif) => owner.sendGifMessage(gif),
            },
        });
    },
    condition: ({ composer, owner, store }) =>
        (store.hasGifPickerFeature || store.self.main_user_id?.is_admin) &&
        !owner.env.inChatter &&
        !composer.message,
    icon: "oi oi-gif-picker",
    name: _t("Add GIFs"),
    setup({ actions }) {
        const ui = useService("ui");
        this.popover = usePopover(ComposerPicker, {
            arrow: false,
            class: ui.isSmall
                ? "o-mail-Composer-pickerBottomSheet d-flex flex-column p-0 position-relative"
                : undefined,
            onClose: () => {
                const activeAction = actions.actionStack.pop();
                activeAction?.actionPanelClose?.();
                actions.activeAction = null;
            },
            useBottomSheet: ui.isSmall,
        });
    },
    sequence: ({ owner }) => (!owner.env.inDiscussApp ? 40 : undefined),
    sequenceQuick: ({ owner }) => (owner.env.inDiscussApp ? 15 : undefined),
    tags: ACTION_TAGS.COMPOSER_PICKER,
});
