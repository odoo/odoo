/** @odoo-module  */

import { useEffect, useService } from "@web/core/utils/hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";

class ButtonBoxDropdown extends Dropdown {
    setup() {
        super.setup();
        useEffect(
            () => {
                this.props.redrawButtons(this.state.open);
                const toggler = this.el.querySelector(".dropdown-toggle");
                if (this.state.open) {
                    toggler.setAttribute("aria-expanded", "true");
                } else {
                    toggler.removeAttribute("aria-expanded");
                }
            },
            () => [this.state.open]
        );
    }
}
ButtonBoxDropdown.props = Object.assign(Object.create(Dropdown.props), {
    redrawButtons: { type: Function },
});

export class ButtonBox extends owl.Component {
    setup() {
        const ui = useService("ui");
        const getMaxButtons = () => {
            return [2, 2, 2, 4, 7, 8, 8][ui.size];
        };

        const dropdown = owl.hooks.useRef("dropdown");

        let visibleButtons, dropDownButtons;

        useEffect(() => {
            const maxButtonsInBox = getMaxButtons();
            visibleButtons = [];
            dropDownButtons = [];
            const children = this.el.children;
            for (let index = 0; index < children.length; index++) {
                const elem = children[index];
                if (elem === dropdown.el) {
                    continue;
                }
                elem.classList.remove("o_hidden");
                if (!elem.classList.contains("o_invisible_modifier")) {
                    if (visibleButtons.length < maxButtonsInBox) {
                        visibleButtons.push(index);
                    } else {
                        elem.classList.add("o_hidden");
                        dropDownButtons.push(index);
                    }
                }
            }
            dropdown.el.classList.toggle("o_hidden", !dropDownButtons.length);
            this.el.classList.toggle("o-full", dropDownButtons.length);
            this.el.classList.toggle("o-not-full", !dropDownButtons.length);
        });

        this.dropdownRedrawButtons = (isOpen) => {
            if (!isOpen) {
                return;
            }
            const dropdownMenu = dropdown.el.querySelector(".dropdown-menu");
            const children = dropdownMenu.children;
            for (let index = 0; index < children.length; index++) {
                const elem = children[index];
                elem.classList.remove("o_hidden");
                if (index in visibleButtons) {
                    elem.classList.add("o_hidden");
                }
            }
        };
    }
}
ButtonBox.template = "web.Form.ButtonBox";
ButtonBox.components = { ButtonBoxDropdown };
