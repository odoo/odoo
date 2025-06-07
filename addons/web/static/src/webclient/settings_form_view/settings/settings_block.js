import { HighlightText } from "../highlight_text/highlight_text";
import { escapeRegExp } from "@web/core/utils/strings";

import { Component, useState, useRef, useEffect, onWillRender, useChildSubEnv } from "@odoo/owl";

export class SettingsBlock extends Component {
    static template = "web.SettingsBlock";
    static components = {
        HighlightText,
    };
    static props = {
        title: { type: String, optional: true },
        tip: { type: String, optional: true },
        slots: { type: Object, optional: true },
        class: { type: String, optional: true },
    };
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
