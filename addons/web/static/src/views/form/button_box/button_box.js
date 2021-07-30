/** @odoo-module  */
import { useEffect } from "@web/core/effect_hook";
import { useService } from "@web/core/service_hook";
import { Dropdown } from "@web/core/dropdown/dropdown";

const DEFAULT_MAX_BUTTONS = 7;

class ButtonBoxDropdown extends Dropdown {
    setup() {
        super.setup();
        useEffect(
            () => this.props.redrawButtons(this.state.open),
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
            return [2, 2, 2, 4][ui.size] || DEFAULT_MAX_BUTTONS;
        };

        const dropdown = owl.hooks.useRef("dropdown");

        let visibleButtons, dropDownButtons;

        useEffect(() => {
            const maxButtonsInBox = 1; //getMaxButtons();
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
            const dropdownMenu = dropdown.el.querySelector(".o_dropdown_menu");
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
