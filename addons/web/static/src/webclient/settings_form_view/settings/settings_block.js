import { useChildSubEnv } from "@web/owl2/utils";
import { HighlightText } from "../highlight_text/highlight_text";

import { Component, computed, proxy, signal, useEffect } from "@odoo/owl";
import { normalize } from "@web/core/l10n/utils";
import { useDomSignal } from "@web/core/utils/hooks";

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
    settingsContainerRef = signal(null);
    settingsContainerTitleRef = signal(null);
    settingsContainerTipRef = signal(null);
    searchState = proxy(this.env.searchState);
    setup() {
        useChildSubEnv({
            showAllContainer: this.showAllContainer,
        });
        const isSearchable = useDomSignal(
            () =>
                !!this.settingsContainerRef()?.querySelector(".o_setting_box.o_searchable_setting")
        );
        useEffect(() => {
            const force = this.searchState.value && !this.showAllContainer() && !isSearchable();
            this.toggleContainer(force);
        });
    }

    showAllContainer = computed(() =>
        normalize([this.props.title, this.props.tip].join()).includes(this.searchState.value)
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
