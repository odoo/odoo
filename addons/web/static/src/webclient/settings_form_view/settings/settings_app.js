import { useLayoutEffect } from "@web/owl2/utils";
import { Component, proxy, signal } from "@odoo/owl";

export class SettingsApp extends Component {
    static template = "web.SettingsApp";
    static props = {
        string: String,
        imgurl: String,
        key: String,
        selectedTab: { type: String, optional: true },
        slots: Object,
    };
    settingsAppRef = signal(null);
    setup() {
        this.state = proxy({
            search: this.env.searchState,
        });
        useLayoutEffect(
            () => {
                const el = this.settingsAppRef();
                if (el) {
                    const force =
                        this.state.search.value &&
                        !el.querySelector(".o_settings_container:not(.d-none)") &&
                        !el.querySelector(".o_setting_box.o_searchable_setting");
                    el.classList.toggle("d-none", force);
                }
            },
            () => [this.state.search.value]
        );
    }
}
