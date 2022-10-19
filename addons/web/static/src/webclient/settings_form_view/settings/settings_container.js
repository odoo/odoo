/** @odoo-module **/

import { HighlightText } from "./../highlight_text/highlight_text";
import { escapeRegExp } from "@web/core/utils/strings";

import { Component, useState, useRef, useEffect, onWillRender, useChildSubEnv } from "@odoo/owl";

export class SettingsContainer extends Component {
    setup() {
        this.state = useState({
            search: this.env.searchState,
        });
        this.showAllContainerState = useState({
            showAllContainer: false,
        });
        useChildSubEnv({
            showAllContainer: this.showAllContainerState,
        });
        this.settingsContainerRef = useRef("settingsContainer");
        this.settingsContainerTitleRef = useRef("settingsContainerTitle");
        this.settingsContainerTipRef = useRef("settingsContainerTip");
        useEffect(
            () => {
                const regexp = new RegExp(escapeRegExp(this.state.search.value), "i");
                const force =
                    this.state.search.value &&
                    !regexp.test([this.props.title, this.props.tip].join()) &&
                    !this.settingsContainerRef.el.querySelector(
                        ".o_setting_box.o_searchable_setting"
                    );
                this.toggleContainer(force);
            },
            () => [this.state.search.value]
        );
        onWillRender(() => {
            const regexp = new RegExp(escapeRegExp(this.state.search.value), "i");
            if (regexp.test([this.props.title, this.props.tip].join())) {
                this.showAllContainerState.showAllContainer = true;
            } else {
                this.showAllContainerState.showAllContainer = false;
            }
        });
    }
    toggleContainer(force) {
        if (this.settingsContainerTitleRef.el) {
            this.settingsContainerTitleRef.el.classList.toggle("d-none", force);
        }
        if (this.settingsContainerTipRef.el) {
            this.settingsContainerTipRef.el.classList.toggle("d-none", force);
        }
        this.settingsContainerRef.el.classList.toggle("d-none", force);
    }
}
SettingsContainer.template = "web.SettingsContainer";
SettingsContainer.components = {
    HighlightText,
};
