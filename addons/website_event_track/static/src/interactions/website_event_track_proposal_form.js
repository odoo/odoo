import { scrollTo } from "@html_builder/utils/scrolling";
import { _t } from "@web/core/l10n/translation";
import { post } from "@web/core/network/http_service";
import { registry } from "@web/core/registry";
import { renderToElement } from "@web/core/utils/render";
import { Interaction } from "@web/public/interaction";

export class WebsiteEventTrackProposalForm extends Interaction {
    static selector = ".o_website_event_track_proposal_form";

    dynamicContent = {
        ".o_wetrack_add_contact_information_checkbox" : { "t-on-click" : this.onAdvancedContactToggle },
        "input[name='partner_name']" : { "t-on-input" : this.onPartnerNameInput },
        ".o_wetrack_proposal_submit_button" : { "t-on-click.prevent.stop" : this.onProposalFormSubmit },
        ".o_wetrack_contact_information" : { "t-att-class": () => ({
            "d-none": !this.useAdvancedContact,
            "o_wetrack_no_contact_mean_error": !this.hasContactMean,
        }) },
        ".o_wetrack_contact_mean": { "t-att-class": () => ({ "is-invalid": !this.hasContactMean }) },
        ".o_wetrack_contact_name_input" : { "t-att-required": () => this.useAdvancedContact },
        ".o_wetrack_proposal_error_section": { "t-att-class": () => ({ "d-none": !this.formErrors.length }) },
    }

    setup() {
        this.useAdvancedContact = false;
        this.hasContactMean = true;
        this.formErrors = [];
    }

    /**
     * Evaluate and return validity of form input fields:
     * - 1) error "invalidFormInputs" : Invalid ones are marked as is-invalid and o_wetrack_input_error.
     * - 2) error "noContactMean" : Contact mean fields are marked as is-invalid and contact
     * section as o_wetrack_no_contact_mean_error if none of them is filled.
     *
     * @returns {Boolean} - True if no error remain, false otherwise
     */
    isFormValid() {
        this.formErrors = [];

        // 1) Valid Form Inputs
        this.el.querySelectorAll(".form-control:not(.o_wetrack_select_tags)").forEach((formControl) => {
            // Validate current input
            const isValid = formControl.checkValidity();
            formControl.classList.toggle("o_wetrack_input_error", !isValid);
            formControl.classList.toggle("is-invalid", !isValid);
            if (!isValid) {
                this.formErrors.push("invalidFormInputs");
            }
        });

        // 2) Advanced Contact Must Have a Contact Mean
        if (this.useAdvancedContact) {
            const phoneInput = this.el.querySelector(".o_wetrack_contact_phone_input");
            const emailInput = this.el.querySelector(".o_wetrack_contact_email_input");
    
            this.hasContactMean = (phoneInput.value || emailInput.value);

            if (!this.hasContactMean) {
                this.formErrors.push("noContactMean");
            }
        }

        // Form Validity and Error Display
        this.updateErrorDisplay();
        return this.formErrors.length === 0;
    }

    /**
     * If there are still errors in form, display the error section and
     * compose the error message accordingly.
     */
    updateErrorDisplay() {
        const errorMessages = [];
        
        if (this.formErrors.includes("invalidFormInputs")) {
            errorMessages.push(_t("Please fill out the form correctly."));
        }

        if (this.formErrors.includes("noContactMean")) {
            errorMessages.push(_t("Please enter either a contact email address or a contact phone number."));
        }

        if (this.formErrors.includes("forbidden")) {
            errorMessages.push(_t("You cannot access this page."));
        }

        const errorElement = this.el.querySelector(".o_wetrack_proposal_error_message");
        errorElement.textContent = errorMessages.join(" ");
    }

    /**
     * Display / Hide Additional Contact Information section when toggling
     * the checkbox on the form o_wetrack_add_contact_information_checkbox.
     * Also empty the email to prevent hidden email format error.
     *
     * @param {Event} ev
     */
    onAdvancedContactToggle(ev) {
        this.useAdvancedContact = !this.useAdvancedContact;
        const contactEmailInput = this.el.querySelector(".o_wetrack_contact_email_input");

        if (!this.useAdvancedContact) {
            contactEmailInput.value = "";
        }
    }

    /**
     * Propagates the new input on speaker name to contact name, as long as the latter
     * is the start of partner name. Otherwise, do not modify existing contact name.
     *
     * @param {Event} ev
     */
    onPartnerNameInput(ev) {
        const partnerNameText = ev.currentTarget.value;
        const contactNameInput = this.el.querySelector(".o_wetrack_contact_name_input");
        if (partnerNameText.startsWith(contactNameInput.value)) {
            contactNameInput.value = partnerNameText;
        }
    }

    /**
     * Submits the form if no errors are present in the form after validation.
     *
     * If the submission succeeds, we replace the form with a template containing a small success
     * message.
     *
     * Then we scroll to the position of the success message so that the user can see it.
     * To do that we have to compute the position of the beginning of the element, relatively to its
     * position and the amount already scrolled, then subtract the floating header menu.
     *
     * @param {Event} ev
     */
    async onProposalFormSubmit(ev) {
        // Prevent further clicking
        const submitButton = this.el.querySelector(".o_wetrack_proposal_submit_button");
        submitButton.classList.add("disabled");
        submitButton.setAttribute("disabled", "disabled");

        // Submission of the form if no errors remain
        if (this.isFormValid()) {
            const formData = new FormData(this.el);
            const eventId = encodeURIComponent(this.el.dataset.eventId);

            const jsonResponse = await this.waitFor(post(`/event/${eventId}/track_proposal/post`, formData));
            this.protectSyncAfterAsync(() => {
                if (jsonResponse.success) {
                    // TODO we really should not remove the whole widget element
                    // like that + probably restore the widget before edit mode etc.
                    const parentEl = this.el.parentNode;
                    this.services["public.interactions"].stopInteractions(this.el);
                    this.el.replaceWith(renderToElement("event_track_proposal_success"));
                    scrollTo(parentEl, { extraOffset: 20, duration: 50 });
                    return;
                } else if (jsonResponse.error) {
                    this.updateErrorDisplay([jsonResponse.error]);
                }
            })();
        }

        // Restore button
        submitButton.classList.remove("disabled");
        submitButton.removeAttribute("disabled");
    }
}

registry
    .category("public.interactions")
    .add("website_event_track.website_event_track_proposal_form", WebsiteEventTrackProposalForm);
