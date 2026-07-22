import { Component, onMounted, onPatched, proxy, signal, t, useProps } from "@odoo/owl";

export class SettingsApp extends Component {
    static template = "web.SettingsApp";
    props = useProps({
        string: t.string(),
        imgurl: t.string(),
        key: t.string(),
        selectedTab: t.string().optional(),
        slots: t.object(),
    });
    settingsAppRef = signal(null);
    setup() {
        this.state = proxy({
            search: this.env.searchState,
        });
        const updateVisibility = () => {
            const el = this.settingsAppRef();
            if (el) {
                const force =
                    this.state.search.value &&
                    !el.querySelector(".o_settings_container:not(.d-none)") &&
                    !el.querySelector(".o_setting_box.o_searchable_setting");
                el.classList.toggle("d-none", force);
            }
        };
        onMounted(updateVisibility);
        onPatched(updateVisibility);
    }
}
