import { onWillRender, useChildSubEnv, useLayoutEffect, useRef, useState } from "@web/owl2/utils";
import { HighlightText } from "../highlight_text/highlight_text";

import { Component } from "@odoo/owl";
import { normalize } from "@web/core/l10n/utils";

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
        useLayoutEffect(
            () => {
                const force =
                    this.state.search.value &&
                    !normalize([this.props.title, this.props.tip].join()).includes(
                        this.state.search.value
                    ) &&
                    !this.settingsContainerRef.el.querySelector(
                        ".o_setting_box.o_searchable_setting"
                    );
                this.toggleContainer(force);
            },
            () => [this.state.search.value]
        );
        onWillRender(() => {
            if (
                normalize([this.props.title, this.props.tip].join()).includes(
                    this.state.search.value
                )
            ) {
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
