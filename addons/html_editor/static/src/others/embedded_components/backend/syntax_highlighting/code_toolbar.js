import { Component } from "@odoo/owl";
import { CopyButton } from "@web/core/copy_button/copy_button";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

export const LANGUAGES = {
    plaintext: "Plain Text",
    markdown: "Markdown",
    javascript: "Javascript",
    typescript: "Typescript",
    jsdoc: "JSDoc",
    java: "Java",
    python: "Python",
    html: "HTML",
    xml: "XML",
    svg: "SVG",
    json: "JSON",
    css: "CSS",
    sass: "SASS",
    scss: "SCSS",
    sql: "SQL",
    diff: "Diff",
};

export class CodeToolbar extends Component {
    static template = "html_editor.CodeToolbar";
    static props = {
        target: { validate: (el) => el.nodeType === Node.ELEMENT_NODE },
        getContent: { type: Function },
        onLanguageChange: { type: Function },
        currentLanguage: { type: String },
        convertToParagraph: { type: Function },
    };
    static components = { Dropdown, DropdownItem, CopyButton };

    setup() {
        super.setup();
        this.languages = LANGUAGES;
    }
}
