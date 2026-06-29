import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

export class A11yNewTabLink extends Interaction {
    static selector = "a[target='_blank']";

    start() {
        const newTabIndicatorEl = this._createNewTabIndicator();
        this.insert(newTabIndicatorEl);
    }

    _createNewTabIndicator() {
        const newTabIndicatorEl = document.createElement("span");
        newTabIndicatorEl.innerText = _t("(Open in new tab)");
        newTabIndicatorEl.classList.add("visually-hidden", "a11y_new_tab_link");

        return newTabIndicatorEl;
    }
}

registry.category("public.interactions").add("website.a11y_new_tab_link", A11yNewTabLink);
