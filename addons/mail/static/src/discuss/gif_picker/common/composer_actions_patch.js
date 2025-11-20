import {
    registerComposerAction,
    pickerOnClick,
    pickerSetup,
} from "@mail/core/common/composer_actions";
import { markup } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { markEventHandled } from "@web/core/utils/misc";
import { useGifPicker } from "./gif_picker";

registerComposerAction("add-gif", {
    condition: ({ composer, owner, store }) =>
        (store.hasGifPickerFeature || store.self_user?.is_admin) &&
        !owner.env.inChatter &&
        !composer.message,
    isPicker: true,
    pickerName: _t("GIF"),
    icon: "oi oi-gif-picker",
    name: _t("Add GIFs"),
    onSelected({ owner }, ev) {
        pickerOnClick(owner, this, ev);
        markEventHandled(ev, "Composer.onClickAddGif");
    },
    setup({ owner }) {
        pickerSetup(this, () =>
            useGifPicker(
                undefined,
                {
                    onSelect: async (gif) => {
                        const href = encodeURI(gif.url);
                        await owner._sendMessage(
                            markup`<a href="${href}" target="_blank" rel="noreferrer noopener">${gif.url}</a>`,
                            {
                                parentId: owner.props.composer.replyToMessage?.id,
                            }
                        );
                    },
                    onClose: () => owner.setActivePicker(null),
                },
                { arrow: false }
            )
        );
    },
    sequence: ({ owner }) => (!owner.env.inDiscussApp ? 40 : undefined),
    sequenceQuick: ({ owner }) => (owner.env.inDiscussApp ? 15 : undefined),
});
