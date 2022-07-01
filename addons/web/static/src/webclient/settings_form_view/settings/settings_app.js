/** @odoo-module **/

const { Component, useState } = owl;

export class SettingsApp extends Component {
    setup() {
        this.state = useState({
            search: this.env.searchValue,
        });
    }
}
SettingsApp.template = "web.SettingsApp";
