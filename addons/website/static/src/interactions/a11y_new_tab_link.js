import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

export class A11yNewTabLink extends Interaction {
    static selector = "a[target='_blank']";

    start() {
        if (this.el.hasAttribute("aria-label")) {
            this.addIndicatorInAriaLabel();
        } else {
            this.addVisuallyHiddenIndicator();
        }
    }

    destroy() {
        const ariaLabel = this.el.getAttribute("aria-label");
        const indicator = ` ${_t("(Open in new tab)")}`;
        if (ariaLabel && ariaLabel.endsWith(indicator)) {
            this.el.setAttribute(
                "aria-label",
                ariaLabel.slice(0, ariaLabel.length - indicator.length)
            );
        }
    }

    addVisuallyHiddenIndicator() {
        const newTabIndicatorEl = document.createElement("span");
        newTabIndicatorEl.textContent = ` ${_t("(Open in new tab)")}`;
        newTabIndicatorEl.classList.add("visually-hidden");

        this.insert(newTabIndicatorEl);
    }

    addIndicatorInAriaLabel() {
        const ariaLabelContent = this.el.getAttribute("aria-label");
        this.el.setAttribute("aria-label", `${ariaLabelContent} ${_t("(Open in new tab)")}`);
    }
}

registry.category("public.interactions").add("website.a11y_new_tab_link", A11yNewTabLink);
