/** @odoo-module **/

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

    onSettingTabClick(key) {
        this.state.selectedTab = key;
        this.env.searchState.value = "";
    }
}
SettingsPage.template = "web.SettingsPage";
