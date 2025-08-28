import { Component, useState, onMounted, useRef } from "@odoo/owl";
import { BuilderComponent } from "./builder_component";
import { BuilderRow } from "./builder_row";

import { basicContainerBuilderComponentProps, useBuilderComponent } from "../utils";

export class BuilderOverlayPanel extends Component {
    static template = "html_builder.BuilderOverlayPanel";
    static components = { BuilderComponent, BuilderRow };
    static props = {
        ...basicContainerBuilderComponentProps,
        label: { type: String, optional: false },
        class: { type: String, option: true },
        icon: { type: String, optional: true },
        slots: { type: Object, optional: true },
        withRow: { type: Object, optional: true },
        fullHeight: { type: Boolean, optional: true },
    };
    static defaultProps = {
        class: "btn-secondary",
        icon: "fa-paint-brush",
        withRow: true,
        fullHeight: false,
    };

    setup() {
        useBuilderComponent();
        this.panelRef = useRef("overlayPanel");
        this.state = useState({
            block: "",
        });
        onMounted(() => {
            const t = document.querySelector(".o_customize_tab").getBoundingClientRect().top + 1;
            const b = document.querySelector(".o_customize_tab").getBoundingClientRect().bottom;
            const optionsContainerEl = this.panelRef.el.closest("div.options-container");

            this.state.block = optionsContainerEl.dataset.containerTitle;

            const newOptionsContainerEl = document.createElement("div");
            newOptionsContainerEl.classList.add(
                "options-container",
                "options-container-overlay",
                "mb-1",
                "position-absolute",
                "d-none"
            );
            newOptionsContainerEl.style.top = t + "px";
            newOptionsContainerEl.style.height = b - t + "px";
            newOptionsContainerEl.appendChild(this.panelRef.el);

            optionsContainerEl.parentElement.append(newOptionsContainerEl);
        });
    }

    nextStatus() {
        const optionsContainerEl = this.panelRef.el.parentElement;
        if (optionsContainerEl.classList.contains("d-none")) {
            optionsContainerEl.classList.remove("d-none");
            optionsContainerEl.classList.add("slideIn");
        } else if (optionsContainerEl.classList.contains("slideIn")) {
            optionsContainerEl.classList.remove("slideIn");
            optionsContainerEl.classList.add("slideOut");
        } else {
            optionsContainerEl.classList.remove("slideOut");
            optionsContainerEl.classList.add("d-none");
        }
    }

    toggleOptionContainers(show) {
        document
            .querySelectorAll("div.options-container:not(.options-container-overlay)")
            .forEach((el) => el.classList.toggle("d-none", !show));
    }

    openOverlay() {
        this.nextStatus();
        setTimeout(() => this.toggleOptionContainers(false), 190);
    }

    closeOverlay() {
        this.toggleOptionContainers(true);
        this.nextStatus();
        setTimeout(() => this.nextStatus(), 190);
    }

    onKeyUp(ev) {
        if (ev.keyCode == 13 && this.panelRef.el.parentElement.classList.contains("slideIn")) {
            this.closeOverlay();
        }
    }
}
