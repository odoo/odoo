import { Component, onWillStart, useEffect, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { loadLanguages } from "@web/core/l10n/translation";
import { toolbarButtonProps } from "@html_editor/main/toolbar/toolbar";
import { user } from "@web/core/user";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";

export class LanguageSelector extends Component {
    static template = "html_editor.LanguageSelector";
    static props = {
        ...toolbarButtonProps,
        onSelected: { type: Function },
        isDisabled: { type: Function, optional: true },
    };
    static components = { Dropdown, DropdownItem };

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            languages: [],
        });
        this.dropdown = useDropdownState();
        onWillStart(() => {
            if (user.userId) {
                loadLanguages(this.orm).then((res) => {
                    this.state.languages = res;
                });
            }
        });
        useEffect(
            (isToolbarVisible) => {
                if (!isToolbarVisible) {
                    this.dropdown.close();
                }
            },
            () => [this.props.isToolbarVisible]
        );
    }
    onSelected(language) {
        this.props.onSelected(language);
    }
}
