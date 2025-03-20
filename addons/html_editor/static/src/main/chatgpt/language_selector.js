import { Component, onWillStart, useState } from "@odoo/owl";
import { useChildRef, useService } from "@web/core/utils/hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { loadLanguages } from "@web/core/l10n/translation";
import { jsToPyLocale } from "@web/core/l10n/utils";
import { toolbarButtonProps } from "@html_editor/main/toolbar/toolbar";
import { user } from "@web/core/user";
import { useDropdownAutoVisibility } from "@html_editor/dropdown_autovisibility_hook";

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
        this.menuRef = useChildRef();
        useDropdownAutoVisibility(this.env.overlayState, this.menuRef);
        onWillStart(() => {
            if (user.userId) {
                const userLang = jsToPyLocale(user.lang);
                loadLanguages(this.orm).then((res) => {
                    const userLangIndex = res.findIndex((lang) => lang[0] === userLang);
                    if (userLangIndex !== -1) {
                        const [userLangItem] = res.splice(userLangIndex, 1);
                        res.unshift(userLangItem);
                    }
                    this.state.languages = res;
                });
            }
        });
    }
    onSelected(language) {
        this.props.onSelected(language);
    }
}
