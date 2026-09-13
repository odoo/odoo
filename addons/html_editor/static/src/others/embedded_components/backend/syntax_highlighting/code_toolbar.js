import { Component, t, useProps } from "@odoo/owl";
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
    static components = { Dropdown, DropdownItem, CopyButton };
    static template = "html_editor.CodeToolbar";

    props = useProps({
        convertToParagraph: t.function(),
        currentLanguage: t.string(),
        getContent: t.function(),
        onLanguageChange: t.function(),
        target: t.customValidator(t.object(), (el) => el.nodeType === Node.ELEMENT_NODE),
        toggleCodeWrap: t.function(),
    });

    languages = LANGUAGES;
}
