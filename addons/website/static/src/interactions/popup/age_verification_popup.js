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
        ".o_age_verification_year_btn": {
            "t-on-click.prevent": this.verifyAgeByYear,
        },
        ".o_age_verification_date_btn": {
            "t-on-click.prevent": this.verifyAgeByDate,
        },
        "#verification_error": {
            "t-att-class": () => ({
                "d-none": !this.showAlert,
            }),
        },
        "input[name='age_verification_birth_year']": {
            "t-att-max": () => DateTime.now().year,
        },
        "input[name^='age_verification_birth_']": {
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
     * Prevent closing the popup via any primary button to avoid bypassing
     * verification.
     *
     * @override
     */
    canBtnPrimaryClosePopup(primaryBtnEl) {
        return false;
    }

    /**
     * Prevent closing the popup on backdrop click to enforce verification.
     *
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
        const dateInputEl = this.el.querySelector("input[name='age_verification_birth_date']");
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
        const yearInputEl = this.el.querySelector("input[name='age_verification_birth_year']");
        const yearVal = Number(yearInputEl.value); // Use `Number` to avoid accepting fractional values.
        const minYear = parseInt(yearInputEl.min);
        const maxYear = parseInt(yearInputEl.max);
        if (!Number.isInteger(yearVal) || yearVal < minYear || yearVal > maxYear) {
            this.inputError = true;
            return;
        }
        const birthDate = DateTime.local(yearVal, 1, 1);
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
        const birthDate = DateTime.local(dateVal.year, dateVal.month, dateVal.day);
        this.handleAgeVerification(birthDate);
    }

    /**
     * Checks if user meets minimum age requirement. Shows alert if user is
     * underage, otherwise hides the popup.
     *
     * @param {DateTime} birthDate - The user's birth date
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
     * @param {DateTime} birthDate - The user's birth date
     * @returns {number} The computed age in years
     */
    calculateAge(birthDate) {
        const today = DateTime.now();
        const age = today.year - birthDate.year;
        const hasBirthdayPassed =
            today.month > birthDate.month ||
            (today.month === birthDate.month && today.day >= birthDate.day);
        return hasBirthdayPassed ? age : age - 1;
    }
}

registry
    .category("public.interactions")
    .add("website.age_verification_popup", AgeVerificationPopup);
