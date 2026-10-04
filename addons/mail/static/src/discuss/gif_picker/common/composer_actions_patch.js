import { registerComposerAction } from "@mail/core/common/composer_actions";
import { markup } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { markEventHandled } from "@web/core/utils/misc";
import { GifPicker } from "./gif_picker";

registerComposerAction("add-gif", {
    condition: ({ composer, owner, store }) =>
        (store.hasGifPickerFeature || store.self_user?.is_admin) &&
        !owner.env.inChatter &&
        !composer.message,
    icon: "gif_box",
    name: _t("Send GIF"),
    onSelected(params, ev) {
        markEventHandled(ev, "Composer.onClickAddGif");
    },
    panel: {
        component: GifPicker,
        name: _t("GIF"),
        props: ({ action, owner }) => ({
            onSelect: async (gif) => {
                const gifUrl = gif.media_formats.tinygif.url;
                const href = encodeURI(gifUrl);
                await owner._sendMessage(
                    markup`<a href="${href}" target="_blank" rel="noreferrer noopener">${gifUrl}</a>`,
                    { parentId: owner.props.composer.replyToMessage?.id }
                );
            },
            onClose: () => action.closePanel(),
        }),
    },
    sequence: ({ owner }) => (!owner.env.inDiscussApp ? 40 : undefined),
    sequenceQuick: ({ owner }) => (owner.env.inDiscussApp ? 15 : undefined),
});
