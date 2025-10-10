import { Component, useState, onMounted, useRef, onWillUnmount } from "@odoo/owl";
import { BuilderComponent } from "./builder_component";
import { BuilderRow } from "./builder_row";

import { basicContainerBuilderComponentProps, useBuilderComponent } from "../utils";

export class BuilderOverlayPanel extends Component {
    static template = "html_builder.BuilderOverlayPanel";
    static components = { BuilderComponent, BuilderRow };
    static props = {
        ...basicContainerBuilderComponentProps,
        label: { type: String, optional: false },
        class: { type: String, optional: true },
        icon: { type: String, optional: true },
        slots: { type: Object, optional: true },
        fullHeight: { type: Boolean, optional: true },
        darkVersion: { type: Boolean, optional: true },
        openByDefault: { type: Boolean, optional: true },
        textContent: { type: String, optional: true },
    };
    static defaultProps = {
        class: "btn-secondary",
        icon: "fa-paint-brush",
        fullHeight: false,
        darkVersion: false,
        openByDefault: false,
        textContent: "",
    };

    setup() {
        useBuilderComponent();
        this.overlayPanelRef = useRef("overlayPanel");
        const buttonRef = useRef("openButton");
        this.state = useState({
            block: "",
        });
        onMounted(() => {
            this.optionsContainerEls = document.querySelectorAll("div.options-container");

            const snippetsTopActionsEl = document.querySelector(".o-snippets-top-actions");
            const snippetsTabsEl = document.querySelector(".o-snippets-tabs");
            const sidebarEl = document.querySelector(".o-website-builder_sidebar");

            const getHeight = (el) => el.getBoundingClientRect().height;

            const top = snippetsTabsEl.bottom + 1;
            const height =
                getHeight(sidebarEl) -
                (getHeight(snippetsTopActionsEl) + getHeight(snippetsTabsEl));

            const overlayPanelEl = this.overlayPanelRef.el;
            overlayPanelEl.style.top = top + "px";
            overlayPanelEl.style.height = height + "px";

            const optionsContainerEl = buttonRef.el.closest("div.options-container");
            this.state.block = optionsContainerEl.dataset.containerTitle;
            optionsContainerEl.parentElement.append(overlayPanelEl);

            if (this.props.openByDefault) {
                this.openOverlay();
            }
        });
        onWillUnmount(() => {
            this.toggleOptionContainers(true);
            this.overlayPanelRef.el.remove();
        });
    }

    updateDisplay(className) {
        const overlayPanelEl = this.overlayPanelRef.el;
        overlayPanelEl.classList.toggle("d-none", className === "d-none");
        overlayPanelEl.classList.toggle("slideIn", className === "slideIn");
        overlayPanelEl.classList.toggle("slideOut", className === "slideOut");
    }

    toggleOptionContainers(show) {
        this.optionsContainerEls.forEach((el) => el.classList.toggle("d-none", !show));
    }

    openOverlay() {
        this.updateDisplay("slideIn");
        setTimeout(() => this.toggleOptionContainers(false), 200);
    }

    closeOverlay() {
        this.toggleOptionContainers(true);
        this.updateDisplay("slideOut");
        setTimeout(() => this.updateDisplay("d-none"), 180);
    }

    onKeyUp(ev) {
        if (ev.keyCode == 9) {
            this.toggleOptionContainers(false);
        }
        if (ev.keyCode == 13) {
            this.closeOverlay();
        }
    }

    onBackdropClick(ev) {
        if (!this.props.fullHeight && ev.target === ev.currentTarget) {
            this.closeOverlay();
        }
    }
}
