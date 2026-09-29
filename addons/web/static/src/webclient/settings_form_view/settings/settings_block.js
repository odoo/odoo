import { useLayoutEffect, useSubEnv } from "@web/owl2/utils";
import { HighlightText } from "../highlight_text/highlight_text";

import { Component, computed, proxy, signal, t, useProps } from "@odoo/owl";
import { normalize } from "@web/core/l10n/utils";

export class SettingsBlock extends Component {
    static template = "web.SettingsBlock";
    static components = {
        HighlightText,
    };
    props = useProps({
        title: t.string().optional(),
        tip: t.string().optional(),
        slots: t.object().optional(),
        class: t.string().optional(),
    });
    settingsContainerRef = signal.ref();
    settingsContainerTitleRef = signal.ref();
    settingsContainerTipRef = signal.ref();
    setup() {
        this.state = proxy({
            search: this.env.searchState,
        });
        useSubEnv({
            showAllContainer: this.showAllContainer,
        });
        // The one `useLayoutEffect` of the settings form view that does not
        // convert to `onMounted` + `onPatched`. It reads its dependency array
        // from a render, which subscribes *this component* to the search value —
        // and nothing else does: a block coming from the `res_config_dev_tool`
        // widget holds a plain `Setting` rather than a `SearchableSetting`, so
        // nothing inside it reads the search, and no parent re-renders it
        // either. Without that subscription the block is never patched and
        // never hides. Binding `d-none` from the template instead deadlocks:
        // the class is derived from a DOM measurement that can only be taken in
        // `onPatched`, which only runs when the render changed the DOM.
        // Removing this hook means deriving the block's visibility from its
        // settings' `visible()` signals rather than from the DOM.
        useLayoutEffect(
            () => {
                const containerEl = this.settingsContainerRef();
                if (!containerEl) {
                    return;
                }
                const force =
                    this.state.search.value &&
                    !this.showAllContainer() &&
                    !containerEl.querySelector(".o_setting_box.o_searchable_setting");
                this.toggleContainer(force);
            },
            () => [this.state.search.value, this.settingsContainerRef()]
        );
    }

    showAllContainer = computed(() =>
        normalize([this.props.title, this.props.tip].join()).includes(this.state.search.value)
    );

    toggleContainer(force) {
        const titleEl = this.settingsContainerTitleRef();
        if (titleEl) {
            titleEl.classList.toggle("d-none", force);
        }
        const tipEl = this.settingsContainerTipRef();
        if (tipEl) {
            tipEl.classList.toggle("d-none", force);
        }
        const containerEl = this.settingsContainerRef();
        if (containerEl) {
            containerEl.classList.toggle("d-none", force);
        }
    }
}
