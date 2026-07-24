import { Component, computed, onMounted, onPatched, proxy, signal } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useService } from "@web/core/utils/hooks";

export class SettingsPage extends Component {
    static template = "web.SettingsPage";
    static components = { Dropdown, DropdownItem };
    static props = {
        modules: Array,
        anchors: Array,
        initialTab: { type: String, optional: true },
        slots: Object,
    };
    settingsRef = signal(null);
    setup() {
        this.uiService = useService("ui");
        this.state = proxy({
            selectedTab: "",
            search: this.env.searchState,
        });

        if (this.props.modules) {
            let selectedTab = this.props.initialTab || this.props.modules[0].key;

            if (browser.location.hash) {
                const hash = browser.location.hash.substring(1);
                if (this.props.modules.map((m) => m.key).includes(hash)) {
                    selectedTab = hash;
                } else {
                    const plop = this.props.anchors.find((a) => a.settingId === hash);
                    if (plop) {
                        selectedTab = plop.app;
                    }
                }
            }

            this.state.selectedTab = selectedTab;
        }

        this.scrollMap = Object.create(null);
        let scrolledTab;
        const restoreTabScroll = () => {
            const settingsEl = this.settingsRef();
            if (!settingsEl || this.state.selectedTab === scrolledTab) {
                return;
            }
            scrolledTab = this.state.selectedTab;
            const { scrollTop } = this.scrollMap[scrolledTab] || 0;
            settingsEl.scrollTop = scrollTop;
            this.tabChangeProm?.resolve();
        };
        onMounted(restoreTabScroll);
        onPatched(restoreTabScroll);
    }

    selectedModule = computed(() =>
        this.props.modules.find((module) => module.key === this.state.selectedTab)
    );

    get invalidApps() {
        const invalidApps = [];
        for (const anchor of this.props.anchors) {
            if (
                anchor.fieldNames.some((fieldName) => this.env.model.root.isFieldInvalid(fieldName))
            ) {
                invalidApps.push(anchor.app);
            }
        }
        return invalidApps;
    }

    onSettingTabClick(key, updateUrl = false) {
        const el = this.settingsRef();
        if (el) {
            const { scrollTop } = el;
            this.scrollMap[this.state.selectedTab] = { scrollTop };
        }
        this.state.selectedTab = key;
        if (updateUrl) {
            browser.location.hash = key;
        }
        this.env.searchState.clearSearch();
    }
}
