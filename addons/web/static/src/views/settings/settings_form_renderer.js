// @ts-check

/** @module @web/views/settings/settings_form_renderer - FormRenderer subclass registering settings-specific sub-components (search highlight, tabs) */

import { useState } from "@odoo/owl";
import { FormRenderer } from "@web/views/form/form_renderer";

import { FormLabelHighlightText } from "./highlight_text/form_label_highlight_text";
import { HighlightText } from "./highlight_text/highlight_text";
import { SearchableSetting } from "./settings/searchable_setting";
import { SettingHeader } from "./settings/setting_header";
import { SettingsApp } from "./settings/settings_app";
import { SettingsBlock } from "./settings/settings_block";
import { SettingsPage } from "./settings/settings_page";
/** FormRenderer subclass that registers settings-specific sub-components. */
export class SettingsFormRenderer extends FormRenderer {
    static components = {
        .../** @type {any} */ (FormRenderer).components,
        SearchableSetting,
        SettingHeader,
        SettingsBlock,
        SettingsPage,
        SettingsApp,
        HighlightText,
        FormLabel: FormLabelHighlightText,
    };
    static props = {
        .../** @type {any} */ (FormRenderer).props,
        initialApp: String,
        slots: Object,
    };

    setup() {
        super.setup();
        this.searchState = useState(this.env.searchState);
    }

    get shouldAutoFocus() {
        return false;
    }
}
