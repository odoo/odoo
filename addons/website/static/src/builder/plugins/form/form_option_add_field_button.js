import { useOperation } from "@html_builder/core/operation_plugin";
import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

const FORM_INNER_SNIPPETS = [
    {
        name: "Title",
        id: "s_inline_text",
        build: (el) => {
            const span = document.createElement("span");
            span.textContent = "Add a Section Title";
            span.className = "h2-fs";
            el.style.textAlign = "center";
            el.replaceChildren(span);
            return el;
        },
    },
    {
        name: "Text",
        id: "s_inline_text",
        build: (el) => {
            el.style.textAlign = "center";
            el.textContent =
                "Add or adjust these fields to collect the information relevant to your needs.";
            return el;
        },
    },
    { name: "Separator", id: "s_hr" },
];

export class FormOptionAddFieldButton extends BaseOptionComponent {
    static template = "website.s_website_form_form_option_add_field_button";
    static props = {
        addField: Function,
        tooltip: String,
    };

    setup() {
        this.callOperation = useOperation();
    }

    addField() {
        this.callOperation(() => {
            this.props.addField(this.env.getEditingElement());
        });
    }
}

export class FormOptionAddContentDropdown extends BaseOptionComponent {
    static template = "website.s_website_form_form_option_add_snippet_dropdown";
    static components = {
        DropdownItem,
        Dropdown,
    };
    static props = {
        addField: Function,
        tooltip: String,
    };

    setup() {
        this.callOperation = useOperation();
        this.snippets = [{ name: "Field", id: "field" }, ...FORM_INNER_SNIPPETS];
    }
    addField(config) {
        this.callOperation(() => {
            this.props.addField(this.env.getEditingElement(), config);
        });
    }
}
