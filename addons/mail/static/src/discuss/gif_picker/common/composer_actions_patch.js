import { pickerGetAnchor, registerComposerAction } from "@mail/core/common/composer_actions";
import { markup } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { usePopover } from "@web/core/popover/popover_hook";
import { markEventHandled } from "@web/core/utils/misc";
import { GifPicker } from "./gif_picker";

registerComposerAction("add-gif", {
    actionPanelComponent: GifPicker,
    actionPanelComponentProps: ({ action, owner }) => ({
        onSelect: async (gif) => {
            const gifUrl = gif.media_formats.tinygif.url;
            const href = encodeURI(gifUrl);
            await owner._sendMessage(
                markup`<a href="${href}" target="_blank" rel="noreferrer noopener">${gifUrl}</a>`,
                { parentId: owner.props.composer.replyToMessage?.id }
            );
        },
        onClose: () => action.actionPanelClose(),
    }),
    actionPanelName: _t("GIF"),
    actionPanelOpen(...args) {
        const anchorEl = pickerGetAnchor(...args);
        this.popover?.open(anchorEl, this.actionPanelComponentProps);
    },
    condition: ({ composer, owner, store }) =>
        (store.hasGifPickerFeature || store.self_user?.is_admin) &&
        !owner.env.inChatter &&
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
    sequence: ({ owner }) => (!owner.env.inDiscussApp ? 40 : undefined),
    sequenceQuick: ({ owner }) => (owner.env.inDiscussApp ? 15 : undefined),
});
