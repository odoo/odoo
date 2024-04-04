/** @odoo-module **/

import { Component, useState, useEffect, useRef } from "@odoo/owl";

export class SettingsApp extends Component {
    setup() {
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
                            ".o_settings_container:not(.d-none)"
                        ) &&
                        !this.settingsAppRef.el.querySelector(
                            ".o_setting_box.o_searchable_setting"
                        );
                    this.settingsAppRef.el.classList.toggle("d-none", force);
                }
            },
            () => [this.state.search.value]
        );
    }
}
SettingsApp.template = "web.SettingsApp";
