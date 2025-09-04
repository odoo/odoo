import { useOperation } from "@html_builder/core/operation_plugin";
import { BaseOptionComponent } from "@html_builder/core/utils";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

const FORM_INNER_SNIPPETS = [
    { name: "Title", id: "s_title", category: "snippet_structure" },
    { name: "Text", id: "s_text_block", category: "snippet_structure" },
    { name: "Separator", id: "s_hr", category: "snippet_content" },
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
