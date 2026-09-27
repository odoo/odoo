import { registry } from '@web/core/registry';
import { Interaction } from '@web/public/interaction';


export class DropdownTypeahead extends Interaction {
    static selector = ".dropdown.o_typeahead, .dropup.o_typeahead";

    dynamicContent = {
        _root: {
            "t-on-shown.bs.dropdown": this.onDropdownShown,
            "t-on-hidden.bs.dropdown": this.onDropdownHidden,
            "t-on-keydown": this.onKeydown,
        },
    };

    setup() {
        this.options = [...this.el.querySelectorAll(".dropdown-item")]
            .map((item) => [item, item.dataset.value ?? item.textContent])
            .map(([item, value]) => [item, value.trim().toLowerCase()]);
        this.query = "";
        this.isDropdownShown = false;
    }

    onDropdownShown() {
        this.isDropdownShown = true;
    }

    onDropdownHidden() {
        this.isDropdownShown = false;
        clearTimeout(this.timeout);
        this.query = "";
    }

    onKeydown(ev) {
        if (!this.isDropdownShown || ev.key.length !== 1) return;

        clearTimeout(this.timeout);
        this.timeout = this.waitForTimeout(() => this.query = "", 700);

        this.query += ev.key.toLowerCase();
        const match = this.options.find(([, value]) => value.startsWith(this.query));

        if (match) {
            match[0].focus();
            ev.preventDefault();
        }
    }
}

registry.category("public.interactions").add("website_sale.dropdown_typeahead", DropdownTypeahead);
