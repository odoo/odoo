import { useLayoutEffect, useRef } from "@web/owl2/utils";
import { Component, proxy } from "@odoo/owl";

export class SettingsApp extends Component {
    static template = "web.SettingsApp";
    static props = {
        string: String,
        imgurl: String,
        key: String,
        selectedTab: { type: String, optional: true },
        slots: Object,
    };
    setup() {
        this.state = proxy({
            search: this.env.searchState,
        });
        this.settingsAppRef = useRef("settingsApp");
        useLayoutEffect(
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
