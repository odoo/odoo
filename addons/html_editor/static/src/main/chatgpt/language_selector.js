import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { loadLanguages } from "@web/core/l10n/translation";
import { toolbarButtonProps } from "@html_editor/main/toolbar/toolbar";

export class LanguageSelector extends Component {
    static template = "html_editor.LanguageSelector";
    static props = toolbarButtonProps;
    static components = { Dropdown, DropdownItem };

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            languages: [],
        });
        onWillStart(() => {
            loadLanguages(this.orm).then((res) => {
                this.state.languages = res;
            });
        });
    }
    onSelected(language) {
        this.props.dispatch("OPEN_CHATGPT_DIALOG", { language });
    }
}
