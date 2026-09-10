import { Component, computed, onMounted, onPatched, proxy, signal, t, useProps } from "@odoo/owl";
import { location } from "@web/core/browser/browser";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useService } from "@web/core/utils/hooks";

export class SettingsPage extends Component {
    static template = "web.SettingsPage";
    static components = { Dropdown, DropdownItem };
    props = useProps({
        modules: t.array(),
        anchors: t.array(),
        initialTab: t.string().optional(),
        slots: t.object(),
    });
    settingsRef = signal.ref();
    setup() {
        this.uiService = useService("ui");
        this.state = proxy({
            selectedTab: "",
            search: this.env.searchState,
        });

        if (this.props.modules) {
            let selectedTab = this.props.initialTab || this.props.modules[0].key;

            if (location.hash) {
                const hash = location.hash.substring(1);
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
        // `useLayoutEffect` only re-ran its callback when a dependency changed.
        // That gating is not incidental here: this callback writes `scrollTop`,
        // so running it on every patch would yank the panel back to the stored
        // offset while the user scrolls or edits a setting, and force a layout
        // each time. `onPatched` has no dependency array, so the check is kept
        // explicitly.
        let lastSettingsEl;
        let lastTab;
        const restoreTabScroll = () => {
            const settingsEl = this.settingsRef();
            if (!settingsEl) {
                return;
            }
            if (settingsEl === lastSettingsEl && this.state.selectedTab === lastTab) {
                return;
            }
            lastSettingsEl = settingsEl;
            lastTab = this.state.selectedTab;

            const { scrollTop } = this.scrollMap[lastTab] || 0;
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
            location.hash = key;
        }
        this.env.searchState.clearSearch();
    }
}
