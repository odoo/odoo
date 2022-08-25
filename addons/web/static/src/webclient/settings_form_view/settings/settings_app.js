/** @odoo-module **/

const { Component, useState } = owl;

export class SettingsApp extends Component {
    setup() {
        this.state = useState({
            search: this.env.searchState,
        });
    }
}
SettingsApp.template = "web.SettingsApp";
