import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class SearchPanel extends Interaction {
    static selector = ".o_portal_search_panel";
    dynamicContent = {
        _root: { "t-on-submit.prevent": this.onSubmit },
        ".dropdown-item": { "t-on-click.prevent.withTarget": this.onDropdownItemClick },
    };

    start() {
        this.adaptSearchLabel();
    }

    adaptSearchLabel() {
        const activeEl = this.el.querySelector(".dropdown-item.active");
        const labelEl = activeEl.cloneNode();
        const noLabelEls = labelEl.querySelectorAll("span.nolabel");
        for (const noLabelEl of noLabelEls) {
            noLabelEl.remove();
        }
        this.el.querySelector("input[name='search']").setAttribute("placeholder", labelEl.textContent.trim());
    }

    onSubmit() {
        const search = new URL(window.location).searchParams;
        search.set("search_in", this.el.querySelector(".dropdown-item.active").getAttribute("href")?.replace("#", "") || "");
        search.set("search", this.el.querySelector("input[name='search']").value);
        window.location.search = search.toString();
    }

    onDropdownItemClick(ev, currentTargetEl) {
        const itemEls = currentTargetEl.closest(".dropdown-menu").querySelectorAll(".dropdown-item");
        for (const itemEl of itemEls) {
            itemEl.classlist.remove("active");
        }
        currentTargetEl.classlist.add("active");
        this.adaptSearchLabel();
    }
}

registry
    .category("public.interactions")
    .add("portal.search_panel", SearchPanel);
