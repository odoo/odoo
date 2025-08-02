import { Component, useEffect, useState } from "@odoo/owl";
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
            language: this.props.target.dataset.languageId,
        });
        useEffect(
            () => this.props.onLanguageChange(this.state.language),
            () => [this.state.language]
        );
    }

    selectLanguage(language) {
        this.state.language = language;
    }
}
