// @ts-check

/** @module @web/views/settings/settings/settings_block - Collapsible group of settings within an app tab with search-based visibility toggling */

import {
    Component,
    onWillRender,
    useChildSubEnv,
    useEffect,
    useRef,
    useState,
} from "@odoo/owl";
import { escapeRegExp } from "@web/core/utils/format/strings";
import { HighlightText } from "@web/views/settings/highlight_text/highlight_text";

/** Collapsible group of settings within an app tab, with search-based visibility. */
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
    /** Initialize reactive state, refs, and search-driven visibility effects. */
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
                        ".o_setting_box.o_searchable_setting",
                    );
                this.toggleContainer(force);
            },
            () => [this.state.search.value],
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
    /**
     * Show or hide the container title, tip, and body based on search match.
     * @param {boolean} force - If true, hide the container elements
     */
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
