import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

export class A11yNewTabLink extends Interaction {
    static selector = "a[target='_blank']";
    dynamicContent = {
        _root: {
            "t-att-aria-label": () => {
                if (this.el.hasAttribute("aria-label")) {
                    return `${this.originalAriaLabel} ${this.openInNewTab}`;
                }
            },
        },
    };

    setup() {
        this.originalAriaLabel = this.el.getAttribute("aria-label");
        this.openInNewTab = _t("(Open in new tab)");
    }

    start() {
        if (!this.el.hasAttribute("aria-label")) {
            const newTabIndicatorEl = document.createElement("span");
            newTabIndicatorEl.textContent = ` ${this.openInNewTab}`;
            newTabIndicatorEl.classList.add("visually-hidden");

            this.insert(newTabIndicatorEl);
        }
    }
}

registry.category("public.interactions").add("website.a11y_new_tab_link", A11yNewTabLink);
