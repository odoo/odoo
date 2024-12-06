import { Component, useEffect, useRef, useState } from "@odoo/owl";
import { isTextNode } from "@web/views/view_compiler";
import { OptionsContainer } from "../components/OptionsContainer";

export class CustomizeTab extends Component {
    static template = "html_builder.CustomizeTab";
    static components = { OptionsContainer };
    static props = {
        currentOptionsContainers: { type: Array, optional: true },
    };
    static defaultProps = {
        currentOptionsContainers: [],
    };

    setup() {
        this.state = useState({
            hasContent: true,
        });
        const contentRef = useRef("content");

        const applyVisibility = () => {
            this.state.hasContent = [...contentRef.el.childNodes].some((el) =>
                isTextNode(el) ? el.textContent !== "" : !el.classList.contains("d-none")
            );
        };

        const observer = new MutationObserver(() => {
            applyVisibility();
        });
        useEffect(
            (contentEl) => {
                if (!contentEl) {
                    return;
                }
                applyVisibility();
                observer.observe(contentEl, {
                    subtree: true,
                    attributes: true,
                    childList: true,
                    attributeFilter: ["class"],
                });
                return () => {
                    observer.disconnect();
                };
            },
            () => [contentRef.el]
        );
    }
}
