/** @odoo-module **/
import { ActionSwiper } from "@web/core/action_swiper/action_swiper";

import { Component, useState, useRef, useEffect } from "@odoo/owl";

export class SettingsPage extends Component {
    setup() {
        this.state = useState({
            selectedTab: "",
            search: this.env.searchState,
        });

        if (this.props.modules) {
            this.state.selectedTab = this.props.initialTab || this.props.modules[0].key;
        }

        this.settingsRef = useRef("settings");
        this.scrollMap = Object.create(null);
        useEffect(
            (settingsEl, currentTab) => {
                if (!settingsEl) {
                    return;
                }

                const { scrollTop } = this.scrollMap[currentTab] || 0;
                settingsEl.scrollTop = scrollTop;
            },
            () => [this.settingsRef.el, this.state.selectedTab]
        );
    }

    getCurrentIndex() {
        return this.props.modules.findIndex((object) => {
            return object.key === this.state.selectedTab;
        });
    }

    hasRightSwipe() {
        return (
            this.env.isSmall && this.state.search.value.length === 0 && this.getCurrentIndex() !== 0
        );
    }
    hasLeftSwipe() {
        return (
            this.env.isSmall &&
            this.state.search.value.length === 0 &&
            this.getCurrentIndex() !== this.props.modules.length - 1
        );
    }
    onRightSwipe() {
        this.state.selectedTab = this.props.modules[this.getCurrentIndex() - 1].key;
    }
    onLeftSwipe() {
        this.state.selectedTab = this.props.modules[this.getCurrentIndex() + 1].key;
    }

    onSettingTabClick(key) {
        if (this.settingsRef.el) {
            const { scrollTop } = this.settingsRef.el;
            this.scrollMap[this.state.selectedTab] = { scrollTop };
        }
        this.state.selectedTab = key;
        this.env.searchState.value = "";
    }
}
SettingsPage.template = "web.SettingsPage";
SettingsPage.components = { ActionSwiper };
SettingsPage.props = {
    modules: Array,
    initialTab: { type: String, optional: 1 },
    slots: Object,
};
