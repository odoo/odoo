import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

export class A11yNewTabLink extends Interaction {
    static selector = "a[target='_blank']";

    start() {
        if (!this._hasNewTabIndicator()) {
            this._createNewTabIndicator();
        }
    }

    destroy() {
        this._getNewTabIndicator()?.remove();
    }

    _getNewTabIndicator() {
        return this.el.querySelector(".a11y_new_tab_link");
    }

    _hasNewTabIndicator() {
        return this._getNewTabIndicator() !== null;
    }

    _createNewTabIndicator() {
        const newTabIndicatorEl = document.createElement("span");
        newTabIndicatorEl.innerText = _t("(Open in new tab)");
        newTabIndicatorEl.classList.add("visually-hidden", "a11y_new_tab_link");

        this.el.appendChild(newTabIndicatorEl);
    }
}

registry.category("public.interactions").add("website.a11y_new_tab_link", A11yNewTabLink);
