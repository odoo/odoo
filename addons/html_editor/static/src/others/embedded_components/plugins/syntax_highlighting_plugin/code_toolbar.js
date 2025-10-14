import { getEmbeddedProps } from "@html_editor/others/embedded_component_utils";
import { Component, onWillDestroy, useEffect, useState } from "@odoo/owl";
import { CopyButton } from "@web/core/copy_button/copy_button";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

export class CodeToolbar extends Component {
    static template = "html_editor.CodeToolbar";
    static props = {
        target: { validate: (el) => el.nodeType === Node.ELEMENT_NODE },
        prismSource: { validate: (el) => el.nodeType === Node.ELEMENT_NODE },
        languages: { type: Object },
        onLanguageChange: { type: Function },
    };
    static components = { Dropdown, DropdownItem, CopyButton };

    setup() {
        super.setup();
        this.state = useState({
            language: getEmbeddedProps(this.props.target).languageId,
        });
        useEffect(
            () => this.props.onLanguageChange(this.state.language),
            () => [this.state.language]
        );
        const observer = new MutationObserver((mutations) => {
            for (const mutation of mutations) {
                if (
                    mutation.type === "attributes" &&
                    mutation.attributeName === "data-embedded-state"
                ) {
                    const languageId = getEmbeddedProps(this.props.target).languageId;
                    if (languageId !== this.state.language) {
                        this.selectLanguage(languageId);
                    }
                }
            }
        });
        observer.observe(this.props.target, { attributes: true });
        onWillDestroy(() => {
            observer.disconnect();
        });
    }

    selectLanguage(language) {
        this.state.language = language;
    }
}
