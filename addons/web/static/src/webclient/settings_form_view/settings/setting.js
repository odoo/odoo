/** @odoo-module **/

import { escapeRegExp } from "@web/core/utils/strings";

import { Component, useState, useChildSubEnv } from "@odoo/owl";

export class Setting extends Component {
    setup() {
        this.state = useState({
            search: this.env.searchState,
            showAllContainer: this.env.showAllContainer,
        });
        // Don't search on a header setting
        if (this.props.type === "header") {
            useChildSubEnv({ searchState: { value: "" } });
        }
        this.labels = this.props.labels || [];
    }
    visible() {
        if (!this.state.search.value) {
            return true;
        }
        // Always shown a header setting
        if (this.props.type === "header") {
            return true;
        }
        if (this.state.showAllContainer.showAllContainer) {
            return true;
        }
        const regexp = new RegExp(escapeRegExp(this.state.search.value), "i");
        if (regexp.test(this.labels.join())) {
            return true;
        }
        return false;
    }

    get classNames() {
        const { class: _class, type } = this.props;
        const classNames = {
            o_setting_box: true,
            o_searchable_setting: this.labels.length && type !== "header",
            [_class]: Boolean(_class),
        };

        return classNames;
    }
}
Setting.template = "web.Setting";
