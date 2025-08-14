import {
    registerComposerAction,
    pickerOnClick,
    pickerSetup,
} from "@mail/core/common/composer_actions";
import { _t } from "@web/core/l10n/translation";
import { markEventHandled } from "@web/core/utils/misc";
import { useGifPicker } from "./gif_picker";

registerComposerAction("add-gif", {
    condition: ({ composer, owner, store }) =>
        (store.hasGifPickerFeature || store.self.main_user_id?.is_admin) &&
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
                    onSelect: (gif) => owner.sendGifMessage(gif),
                    onClose: () => owner.setActivePicker(null),
                },
                { arrow: false }
            )
        );
    },
    sequence: ({ owner }) => (!owner.env.inDiscussApp ? 40 : undefined),
    sequenceQuick: ({ owner }) => (owner.env.inDiscussApp ? 15 : undefined),
});
