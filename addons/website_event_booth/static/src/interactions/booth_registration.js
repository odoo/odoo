import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { _t } from "@web/core/l10n/translation";
import { post } from "@web/core/network/http_service";
import { rpc } from "@web/core/network/rpc";
import { redirect } from "@web/core/utils/urls";

export class BoothRegistration extends Interaction {
    static selector = ".o_wbooth_registration";
    dynamicContent = {
        "input[name='booth_category_id']": {
            "t-on-change.prevent.withTarget": this.onBoothTypeChange,
        },
        ".form-check > input[type='checkbox']": {
            "t-on-change.withTarget": this.onBoothChange,
        },
        ".o_wbooth_registration_submit": {
            "t-on-click.prevent": this.onSubmitClick,
        },
        ".o_wbooth_registration_confirm": {
            "t-on-click.prevent.stop.withTarget": this.onConfirmClick,
        },
        ".o_wbooth_registration_error_section": {
            "t-att-class": () => ({
                "d-none": !this.inError,
            }),
        },
        "button.o_wbooth_registration_submit": {
            "t-att-disabled": () => this.isSelectionEmpty ? true : undefined,
        },
    };

    setup() {
        this.inError = false;
        this.boothCache = {};
        this.isFirstRender = true;

        this.eventId = parseInt(this.el.dataset.eventId);

        this.activeBoothCategoryId = false;
        this.selectedBoothIds = [];
        this.selectedBoothCategory = this.el.querySelector("input[name='booth_category_id']:checked");
        if (this.selectedBoothCategory) {
            const boothEl = this.el.querySelector(".o_wbooth_booths");
            this.selectedBoothIds = boothEl.dataset.selectedBoothIds.split(",").map(Number);
            this.activeBoothCategoryId = this.selectedBoothCategory.value;
            this.updateAvailableBoothsUI();
        }
    }

    async checkBoothsAvailability(eventBoothIds) {
        const data = await this.waitFor(rpc("/event/booth/check_availability", {
            event_booth_ids: eventBoothIds,
        }));
        if (data && data.unavailable_booths.length) {
            const boothIdEls = this.el.querySelectorAll("input[name='event_booth_ids']");
            for (const boothIdEl of boothIdEls) {
                if (data.unavailable_booths.includes(parseInt(boothIdEl.value))) {
                    boothIdEl.closest(".form-check").classList.add("text-danger");
                }
            }
            const unavailableBoothAlertEl = this.el.querySelector(".o_wbooth_unavailable_booth_alert");
            unavailableBoothAlertEl.classList.remove("d-none");
            return false;
        }
        return true;
    }

    countSelectedBooths() {
        return this.el.querySelectorAll(".form-check > input[type='checkbox']:checked").length;
    }

    updateBoothsList() {
        const boothsElem = this.el.querySelector(".o_wbooth_booths");
        boothsElem.replaceChildren();
        this.renderAt("event_booth_checkbox_list", {
            "event_booth_ids": this.boothCache[this.activeBoothCategoryId],
            "selected_booth_ids": this.isFirstRender ? this.selectedBoothIds : [],
        }, boothsElem);
        this.isFirstRender = false;
    }

    /**
     * Check if the confirmation form is valid by testing each of its inputs
     *
     * @param formEl
     * @return {boolean} - true if no errors else false
     */
    checkConfirmationForm(formEl) {
        const formControlEls = formEl.querySelectorAll(".form-control");
        const formErrors = [];
        for (const formControlEl of formControlEls) {
            formControlEl.classList.remove("is-invalid");
            if (!formControlEl.checkValidity()) {
                formControlEl.classList.add("is-invalid");
                formErrors.push("invalidFormInputs");
            }
        }
        this.updateErrorDisplay(formErrors);
        return formErrors.length === 0;
    }

    showBoothCategoryDescription() {
        const boothCategoryDescriptionEls = this.el.querySelectorAll(".o_wbooth_booth_category_description");
        for (const boothCategoryDescriptionEl of boothCategoryDescriptionEls) {
            boothCategoryDescriptionEl.classList.add("d-none");
        }
        const activeBoothEl = this.el.querySelector("#o_wbooth_booth_description_" + this.activeBoothCategoryId);
        activeBoothEl.classList.remove("d-none");
    }

    /**
     * Display the errors with a custom message when confirming
     * the registration if there is any.
     *
     * @param errors
     */
    updateErrorDisplay(errors) {
        this.inError = errors.length;

        const errorMessages = [];
        if (errors.includes("invalidFormInputs")) {
            errorMessages.push(_t("Please fill out the form correctly."));
        }
        if (errors.includes("boothError")) {
            errorMessages.push(_t("Booth registration failed."));
        }
        if (errors.includes("boothCategoryError")) {
            errorMessages.push(_t("The booth category doesn't exist."));
        }

        const errorMessageEl = this.el.querySelector(".o_wbooth_registration_error_message");
        errorMessageEl.textContent = errorMessages.join(" ");
        errorMessageEl.dispatchEvent(new Event("change"));
    }

    /**
     * Load all the booths related to the activeBoothCategoryId booth category and
     * add them to a local dictionary to avoid making rpc each time the
     * user change the booth category.
     *
     * Then the selection input will be filled with the fetched booth values.
     */
    async updateAvailableBoothsUI() {
        if (this.boothCache[this.activeBoothCategoryId] === undefined) {
            const data = await this.waitFor(rpc("/event/booth_category/get_available_booths", {
                event_id: this.eventId,
                booth_category_id: this.activeBoothCategoryId,
            }));
            if (data) {
                this.boothCache[this.activeBoothCategoryId] = data;
            }
        }
        this.updateBoothsList();
        this.showBoothCategoryDescription();
        this.isSelectionEmpty = !!this.countSelectedBooths().length;
    }

    /**
     * @param {Event} ev
     * @param {HTMLElement} currentTargetEl
     */
    onBoothTypeChange(ev, currentTargetEl) {
        this.activeBoothCategoryId = parseInt(currentTargetEl.value);
        this.updateAvailableBoothsUI();
    }

    /**
     * @param {Event} ev
     * @param {HTMLElement} currentTargetEl
     */
    onBoothChange(ev, currentTargetEl) {
        currentTargetEl.closest(".form-check").classList.remove("text-danger");
        this.isSelectionEmpty = !!this.countSelectedBooths().length;
    }

    async onSubmitClick() {
        const selectedBoothEls = this.el.querySelectorAll("input[name=event_booth_ids]:checked");
        const selectedBoothIds = [...selectedBoothEls].map((el) => parseInt(el.value));
        const data = await this.waitFor(this.checkBoothsAvailability(selectedBoothIds));
        if (data) {
            this.el.querySelector(".o_wbooth_registration_form").submit();
        }
    }

    /**
     * @param {Event} ev
     * @param {HTMLElement} currentTargetEl
     */
    async onConfirmClick(ev, currentTargetEl) {
        currentTargetEl.classList.add("disabled");
        currentTargetEl.disabled = true;

        const formEl = this.el.querySelector("#o_wbooth_contact_details_form");
        if (this.checkConfirmationForm(formEl)) {
            const formData = new FormData(formEl);
            const jsonResponse = await this.waitFor(post(`/event/${encodeURIComponent(this.el.dataset.eventId)}/booth/confirm`, formData));
            if (jsonResponse.success) {
                this.el.querySelector(".o_wevent_booth_order_progress").remove();
                const boothCategoryId = this.el.querySelector("input[name=booth_category_id]").value;
                this.renderAt("event_booth_registration_complete", {
                    booth_category_id: boothCategoryId,
                    event_id: this.eventId,
                    event_name: jsonResponse.event_name,
                    contact: jsonResponse.contact,
                }, formEl, "afterend");
                formEl.remove();
            } else if (jsonResponse.redirect) {
                redirect(jsonResponse.redirect);
            } else if (jsonResponse.error) {
                this.updateErrorDisplay(jsonResponse.error);
            }
        }

        currentTargetEl.classList.remove("disabled");
        currentTargetEl.removeAttribute("disabled");
    }
}

registry
    .category("public.interactions")
    .add("website_event_booth.booth_registration", BoothRegistration);
