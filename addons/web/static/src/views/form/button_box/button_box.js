/** @odoo-module  */
import { useEffect } from "@web/core/effect_hook";
import { browser } from "@web/core/browser/browser";

export class ButtonBox extends owl.Component {
    setup() {
        const dropdown = owl.hooks.useRef("dropdown");

        const maxButtonsInBox = 3;

        let visibleButtons, dropDownButtons;
        useEffect(() => {
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
        });

        let timeoutId;
        this.beforeOpenDropdown = () => {
            browser.clearTimeout(timeoutId);
            timeoutId = browser.setTimeout(() => {
                const children = dropdown.el.querySelector(".o_dropdown_menu").children;
                for (let index = 0; index < children.length; index++) {
                    const elem = children[index];
                    elem.classList.remove("o_hidden");
                    if (index in visibleButtons) {
                        elem.classList.add("o_hidden");
                    }
                }
            });
        };
    }
}
ButtonBox.template = "web.Form.ButtonBox";
