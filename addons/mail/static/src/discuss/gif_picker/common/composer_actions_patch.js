import {
    composerActionsRegistry,
    pickerOnClick,
    pickerSetup,
} from "@mail/core/common/composer_actions";
import { _t } from "@web/core/l10n/translation";
import { markEventHandled } from "@web/core/utils/misc";
import { useGifPicker } from "./gif_picker";

composerActionsRegistry.add("add-gif", {
    condition: (component) =>
        (component.store.hasGifPickerFeature || component.store.self.main_user_id?.is_admin) &&
        !component.env.inChatter &&
        !component.props.composer.message,
    isPicker: true,
    pickerName: _t("GIF"),
    icon: "oi oi-gif-picker",
    iconLarge: "oi fa-lg oi-gif-picker",
    name: _t("Add GIFs"),
    onSelected: (component, action, ev) => {
        pickerOnClick(component, action, ev);
        markEventHandled(ev, "Composer.onClickAddGif");
    },
    setup(component) {
        pickerSetup(this, () =>
            useGifPicker(
                undefined,
                {
                    onSelect: (gif) => component.sendGifMessage(gif),
                    onClose: () => component.setActivePicker(null),
                },
                { arrow: false }
            )
        );
    },
    sequence: (component) => (!component.env.inDiscussApp ? 40 : undefined),
    sequenceQuick: (component) => (component.env.inDiscussApp ? 15 : undefined),
});
