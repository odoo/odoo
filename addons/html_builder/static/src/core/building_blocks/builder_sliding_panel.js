import { useRef } from "@web/owl2/utils";
import { Component, onMounted, onWillUnmount, props, proxy, t } from "@odoo/owl";
import { BuilderComponent } from "./builder_component";
import { BuilderRow } from "./builder_row";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";

import { useBuilderComponent } from "../utils";

export class BuilderSlidingPanel extends Component {
    static template = "html_builder.BuilderSlidingPanel";
    static components = { BuilderComponent, BuilderRow };
    props = props({
        // basicContainerBuilderComponentProps (converted inline)
        id: t.string().optional(),
        applyTo: t.string().optional(),
        preview: t.boolean().optional(),
        inheritedActions: t.array(t.string()).optional(),

        action: t.string().optional(),
        actionParam: t.any().optional(),

        // Shorthand actions.
        classAction: t.any().optional(),
        attributeAction: t.any().optional(),
        dataAttributeAction: t.any().optional(),
        styleAction: t.any().optional(),

        label: t.string(),
        extraClasses: t.string().optional(""),
        fullHeight: t.boolean().optional(false),
        darkBackground: t.boolean().optional(false),
        openByDefault: t.boolean().optional(false),
    });

    setup() {
        useBuilderComponent();
        this.slidingPanelRef = useRef("slidingPanel");
        this.openButtonRef = useRef("openButton");
        this.state = proxy({
            optionContainerName: "",
            contentRendered: this.props.openByDefault,
        });
        onMounted(() => {
            const slidingPanelEl = this.slidingPanelRef.el;
            const optionsContainerEl = slidingPanelEl.closest("div.options-container");
            this.state.optionContainerName = optionsContainerEl.dataset.containerTitle;
            optionsContainerEl.parentElement.append(slidingPanelEl);

            if (this.props.openByDefault) {
                this.showSlidingPanel();
            }
        });
        useHotkey("escape", this.hideSlidingPanel.bind(this), {
            isAvailable: () => !this.slidingPanelRef.el.classList.contains("d-none"),
        });
        onWillUnmount(() => {
            clearTimeout(this.updateDisplayTimeout);
            this.slidingPanelRef.el.remove();
        });
    }

    updateDisplay(className) {
        const slidingPanelEl = this.slidingPanelRef.el;
        if (!slidingPanelEl) {
            return;
        }
        slidingPanelEl.classList.remove(
            "d-none",
            "d-block",
            "hb-panel-slide-in",
            "hb-panel-slide-out"
        );
        slidingPanelEl.classList.add(className);
    }

    showSlidingPanel() {
        this.state.contentRendered = true;
        this.updateDisplay("hb-panel-slide-in");
        this.updateDisplayTimeout = setTimeout(() => this.updateDisplay("d-block"), 200);
    }

    hideSlidingPanel() {
        this.updateDisplay("hb-panel-slide-out");
        // We set a timeout slightly shorter than 200 because some flicker may
        // happen otherwise.
        this.updateDisplayTimeout = setTimeout(() => {
            this.updateDisplay("d-none");
            this.openButtonRef.el.focus();
        }, 180);
    }

    onBackdropClick(ev) {
        if (!this.props.fullHeight && ev.target === ev.currentTarget) {
            this.hideSlidingPanel();
        }
    }
}
