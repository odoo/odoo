import { Component, onMounted, onWillUnmount, proxy, signal, t, useProps } from "@odoo/owl";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { BuilderComponent } from "./builder_component";
import { BuilderRow } from "./builder_row";

import { basicContainerBuilderComponentProps, useBuilderComponent } from "../utils";

export class BuilderSlidingPanel extends Component {
    static template = "html_builder.BuilderSlidingPanel";
    static components = { BuilderComponent, BuilderRow };

    props = useProps({
        ...basicContainerBuilderComponentProps,
        label: t.string(),
        extraClasses: t.string().optional(""),
        icon: t.string().optional(),
        fullHeight: t.boolean().optional(false),
        darkBackground: t.boolean().optional(false),
        openByDefault: t.boolean().optional(false),
        onClose: t.function().optional(),
    });

    slidingPanelRef = signal.ref();
    openButtonRef = signal.ref();

    setup() {
        useBuilderComponent(this.props);
        this.state = proxy({
            optionContainerName: "",
            displayClass: "d-none",
            contentRendered: this.props.openByDefault,
        });
        onMounted(() => {
            const slidingPanelEl = this.slidingPanelRef();
            const optionsContainerEl = slidingPanelEl.closest("div.options-container");
            this.state.optionContainerName = optionsContainerEl.dataset.containerTitle;
            optionsContainerEl.parentElement.append(slidingPanelEl);

            if (this.props.openByDefault) {
                this.showSlidingPanel();
            }
        });
        useHotkey("escape", this.hideSlidingPanel.bind(this), {
            isAvailable: () => this.state.displayClass != "d-none",
        });
        onWillUnmount(() => {
            clearTimeout(this.updateDisplayTimeout);
            this.slidingPanelRef().remove();
        });
    }

    showSlidingPanel() {
        this.state.contentRendered = true;
        this.state.displayClass = "hb-panel-slide-in";
        this.updateDisplayTimeout = setTimeout(() => (this.state.displayClass = "d-block"), 200);
    }

    hideSlidingPanel() {
        this.state.displayClass = "hb-panel-slide-out";
        this.updateDisplayTimeout = setTimeout(() => {
            this.state.displayClass = "d-none";
            this.openButtonRef().focus();
            this.props.onClose?.();
        }, 200);
    }

    onBackdropClick(ev) {
        if (!this.props.fullHeight && ev.target === ev.currentTarget) {
            this.hideSlidingPanel();
        }
    }
}
