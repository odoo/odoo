/** @odoo-module **/
import { ActionSwiper } from "@web/core/action_swiper/action_swiper";

const { Component, useState } = owl;

export class SettingsPage extends Component {
    setup() {
        this.state = useState({
            selectedTab: "",
            search: this.env.searchState,
        });

        if (this.props.modules) {
            this.state.selectedTab = this.props.initialTab || this.props.modules[0].key;
        }
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
        this.state.selectedTab = key;
        this.env.searchState.value = "";
    }
}
SettingsPage.template = "web.SettingsPage";
SettingsPage.components = { ActionSwiper };
