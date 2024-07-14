/** @odoo-module **/

import { renderToString } from "@web/core/utils/render";

export class MobileInputBottomSheet {
    constructor(options) {
        this.type = options.type || "text";
        this.placeholder = options.placeholder || "";
        this.label = options.label || this.placeholder;
        this.value = options.value || "";
        this.buttonText = options.buttonText;
        this.element = options.element;
        this.onTextChange = options.onTextChange || function () {};
        this.onValidate = options.onValidate || function () {};

        document.body.insertAdjacentHTML(
            "beforeend",
            renderToString("sign.MobileInputBottomSheet", this)
        );
        this.el = document.body.lastChild;
        this.registerEvents();
    }

    registerEvents() {
        const field = this.el.querySelector(".o_sign_item_bottom_sheet_field");
        const nextButton = this.el.querySelector(".o_sign_next_button");

        if (field) {
            field.addEventListener("blur", () => {
                this._onBlurField();
            });
            field.addEventListener("keyup", () => {
                this._onKeyUpField();
            });
        }

        if (nextButton) {
            nextButton.addEventListener("click", () => {
                this._onClickNext();
            });
        }
    }

    updateInputText(text) {
        this.value = text;
        this.el.querySelector(".o_sign_item_bottom_sheet_field").value = text;
        this._toggleButton();
    }

    show() {
        // hide previous bottom sheet
        const bottomSheet = document.querySelector(".o_sign_item_bottom_sheet.show");
        if (bottomSheet) {
            bottomSheet.classList.remove("show");
        }

        this._toggleButton();
        setTimeout(() => this.el.classList.add("show"));
        this.el.querySelector(".o_sign_item_bottom_sheet_field").focus();
    }

    hide() {
        this.el.classList.remove("show");
        this.el.addEventListener("transitionend", () => (this.el.style.display = "none"), {
            once: true,
        });
    }

    _toggleButton() {
        const buttonNext = this.el.querySelector(".o_sign_next_button");
        this.value.length
            ? buttonNext.removeAttribute("disabled")
            : buttonNext.setAttribute("disabled", "disabled");
    }

    _updateText() {
        this.value = this.el.querySelector(".o_sign_item_bottom_sheet_field").value;
        this.onTextChange(this.value);
        this._toggleButton();
    }

    _onBlurField() {
        this._updateText();
    }

    _onClickNext() {
        this.onValidate(this.value);
    }

    _onKeyUpField() {
        this._updateText();
    }
}
