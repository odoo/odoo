import { registry } from "@web/core/registry";
import { Popup } from "@website/interactions/popup/popup";

const { DateTime } = luxon;

export class AgeVerificationPopup extends Popup {
    static selector = ".s_popup.s_age_verification_popup";
    dynamicContent = {
        ...this.dynamicContent,
        _root: {
            ...this.dynamicContent._root,
            "t-att-data-age-verification-pending": () => String(!this.popupAlreadyShown),
        },
        ".o_age_verification_yes_btn": {
            "t-on-click.prevent": this.hidePopup,
        },
        ".o_age_verification_no_btn": {
            "t-on-click.prevent": () => {
                this.showAlert = true;
            },
        },
        ".o_age_verify_year_btn": {
            "t-on-click.prevent": this.verifyAgeByYear,
        },
        ".o_age_verify_date_btn": {
            "t-on-click.prevent": this.verifyAgeByDate,
        },
        "#verification_error": {
            "t-att-class": () => ({
                "d-none": !this.showAlert,
            }),
        },
        ".o_age_verification_birth_year": {
            "t-att-max": () => new Date().getFullYear(),
        },
        ".form-control": {
            "t-att-class": () => ({ "is-invalid": this.inputError }),
        },
    };

    setup() {
        super.setup();
        this.inputError = false;
        this.showAlert = false;
    }

    start() {
        super.start();
        this.initDatepicker();
    }

    /**
     * @override
     */
    canBtnPrimaryClosePopup(primaryBtnEl) {
        return false;
    }

    /**
     * @override
     */
    onBackdropModalClick(ev) {
        return;
    }

    /**
     * Initializes and enables the date picker when the birth date input is
     * present, and registers required cleanups.
     */
    initDatepicker() {
        const dateInputEl = this.el.querySelector(".o_age_verification_birth_date");
        if (!dateInputEl) {
            return;
        }
        this.datePicker = this.services.datetime_picker.create({
            target: dateInputEl,
            pickerProps: {
                type: "date",
                minDate: DateTime.local(1900, 1, 1),
                maxDate: DateTime.now(),
            },
        });
        this.registerCleanup(this.datePicker.enable());
        this.registerCleanup(this.datePicker.close);
    }

    /**
     * Validates the birth year input and triggers age verification.
     */
    verifyAgeByYear() {
        const yearInputEl = this.el.querySelector(".o_age_verification_birth_year");
        const yearVal = Number(yearInputEl.value);
        const minYear = parseInt(yearInputEl.min);
        const maxYear = parseInt(yearInputEl.max);
        if (!yearVal || !Number.isInteger(yearVal) || yearVal < minYear || yearVal > maxYear) {
            this.inputError = true;
            return;
        }
        const birthDate = new Date(yearVal, 0, 1);
        this.handleAgeVerification(birthDate);
    }

    /**
     * Validates the selected date and triggers age verification.
     */
    verifyAgeByDate() {
        const dateVal = this.datePicker.state.value;
        if (!dateVal) {
            this.inputError = true;
            return;
        }
        const birthDate = new Date(dateVal.year, dateVal.month - 1, dateVal.day);
        this.handleAgeVerification(birthDate);
    }

    /**
     * Checks if user meets minimum age requirement. Shows alert if user is
     * underage, otherwise hides the popup.
     *
     * @param {Date} birthDate - The user's birth date
     */
    handleAgeVerification(birthDate) {
        this.inputError = false;
        const age = this.calculateAge(birthDate);
        const minAge = parseInt(this.modalEl.dataset.minAge);
        if (age < minAge) {
            this.showAlert = true;
        } else {
            this.showAlert = false;
            this.hidePopup();
        }
    }

    /**
     * Calculates the user's age based on the given birth date.
     *
     * @param {Date} birthDate - The user's birth date
     * @returns {number} The computed age in years
     */
    calculateAge(birthDate) {
        const today = new Date();
        const age = today.getFullYear() - birthDate.getFullYear();
        const hasBirthdayPassed =
            today.getMonth() > birthDate.getMonth() ||
            (today.getMonth() === birthDate.getMonth() && today.getDate() >= birthDate.getDate());
        return hasBirthdayPassed ? age : age - 1;
    }
}

registry
    .category("public.interactions")
    .add("website.age_verification_popup", AgeVerificationPopup);
