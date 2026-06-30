import { registerComposerAction, pickerGetAnchor } from "@mail/core/common/composer_actions";
import { markup } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { markEventHandled } from "@web/core/utils/misc";
import { GifPicker } from "./gif_picker";
import { usePopover } from "@web/core/popover/popover_hook";

registerComposerAction("add-gif", {
    actionPanelComponent: GifPicker,
    actionPanelComponentProps: ({ action, replyToMessageId, sendGifMessage }) => ({
        onSelect: async (gif) => {
            const href = encodeURI(gif.url);
            await sendGifMessage(
                markup`<a href="${href}" target="_blank" rel="noreferrer noopener">${gif.url}</a>`,
                {
                    parentId: replyToMessageId(),
                }
            );
        },
        onClose: () => action.actionPanelClose(),
    }),
    actionPanelName: _t("GIF"),
    actionPanelOpen(...args) {
        const anchorEl = pickerGetAnchor(...args);
        this.popover?.open(anchorEl, this.actionPanelComponentProps);
    },
    condition: ({ composer, inChatter, store }) =>
        (store.hasGifPickerFeature || store.self_user?.is_admin) &&
        !inChatter() &&
        !composer.message,
    icon: "oi oi-gif-picker",
    name: _t("Send GIF"),
    onSelected(params, ev) {
        markEventHandled(ev, "Composer.onClickAddGif");
    },
    setup({ store }) {
        if (store.env.services.ui.isSmall) {
            return;
        }
        this.popover = usePopover(GifPicker, {
            arrow: false,
            onClose: () => this.actionPanelClose(),
        });
    },
    sequence: ({ inDiscussApp }) => (!inDiscussApp() ? 40 : undefined),
    sequenceQuick: ({ inDiscussApp }) => (inDiscussApp() ? 15 : undefined),
});
