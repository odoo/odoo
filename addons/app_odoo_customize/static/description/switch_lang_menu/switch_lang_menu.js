/** @odoo-module **/

import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";
import { symmetricalDifference } from "@web/core/utils/arrays";

import { Component, useState } from "@odoo/owl";

export class SwitchLangMenu extends Component {
    setup() {
        this.LangService = useService("Lang");
        this.currentLang = this.LangService.currentLang;
        this.state = useState({ langToSet: [] });
    }

    setLang(LangId) {
        this.state.langToSet = symmetricalDifference(this.state.langToSet, [
            LangId,
        ]);
        browser.clearTimeout(this.toggleTimer);
        this.toggleTimer = browser.setTimeout(() => {
            this.LangService.set2Lang("toggle", ...this.state.langToSet);
        }, this.constructor.toggleDelay);
    }

    logIntoLang(LangId) {
        browser.clearTimeout(this.toggleTimer);
        this.LangService.set2Lang("loginto", LangId);
    }

    get selectedCompanies() {
        return symmetricalDifference(
            this.LangService.allowedLangIds,
            this.state.langToSet
        );
    }
}
SwitchLangMenu.template = "web.SwitchLangMenu";
SwitchLangMenu.components = { Dropdown, DropdownItem };
SwitchLangMenu.toggleDelay = 1000;

export const systrayItem = {
    Component: SwitchLangMenu,
    isDisplayed(env) {
        const { availableCompanies } = env.services.Lang;
        return Object.keys(availableCompanies).length > 1;
    },
};

registry.category("systray").add("SwitchLangMenu", systrayItem, { sequence: 1 });
