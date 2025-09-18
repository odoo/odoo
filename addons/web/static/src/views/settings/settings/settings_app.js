// @ts-check

/** @module @web/views/settings/settings/settings_app - Container for a single app's settings tab content, hidden when search yields no matches */

import { Component, useEffect, useRef, useState } from "@odoo/owl";

/** Container for a single app's settings tab content (hidden when search yields no matches). */
export class SettingsApp extends Component {
    static template = "web.SettingsApp";
    static props = {
        string: String,
        imgurl: String,
        key: String,
        selectedTab: { type: String, optional: 1 },
        slots: Object,
    };
    /**
     * Track search state and toggle `d-none` on the app container when a search
     * is active but no visible settings or containers remain inside this app.
     */
    setup() {
        /** @type {{ search: { value: string } }} */
        this.state = useState({
            search: this.env.searchState,
        });
        this.settingsAppRef = useRef("settingsApp");
        useEffect(
            () => {
                if (this.settingsAppRef.el) {
                    const force =
                        this.state.search.value &&
                        !this.settingsAppRef.el.querySelector(
                            ".o_settings_container:not(.d-none)",
                        ) &&
                        !this.settingsAppRef.el.querySelector(
                            ".o_setting_box.o_searchable_setting",
                        );
                    this.settingsAppRef.el.classList.toggle("d-none", force);
                }
            },
            () => [this.state.search.value],
        );
    }
}
