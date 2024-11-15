import {
    composerActionsRegistry,
    pickerOnClick,
    pickerSetup,
} from "@mail/core/common/composer_actions";
import { useComponent } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { markEventHandled } from "@web/core/utils/misc";
import { useGifPicker } from "./gif_picker";

composerActionsRegistry.add("add-gif", {
    condition: (component) =>
        (component.store.hasGifPickerFeature || component.store.self.isAdmin) &&
        !component.env.inChatter &&
        !component.props.composer.message,
    isPicker: true,
    pickerName: _t("GIF"),
    icon: "oi oi-gif-picker",
    name: _t("Add GIFs"),
    onClick: (component, action, ev) => {
        pickerOnClick(component, action, ev);
        markEventHandled(ev, "Composer.onClickAddGif");
    },
    setup: (action) => {
        const component = useComponent();
        pickerSetup(action, () =>
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
