import { registry } from "@web/core/registry";
import { renderToMarkup } from "@web/core/utils/render";
import { Interaction } from "@web/public/interaction";

export class StateFormField extends Interaction {
    static selector =
        ".s_website_form:has([name='country_id']) .s_website_form_input[data-link-state-to-country='true']";
    dynamicSelectors = {
        ...this.dynamicSelectors,
        _countryField: () =>
            this.el
                .closest(".s_website_form")
                .querySelector(".s_website_form_input[name='country_id']"),
    };
    dynamicContent = {
        _root: {
            "t-on-change": this.onStateFieldChange,
            "t-out": this.getStateOptions,
        },
        _countryField: {
            "t-on-change": this.onCountryFieldChange,
        },
    };

    setup() {
        // Cloning ensures we keep a detached copy
        this.allOptions = Array.from(this.el.querySelectorAll("option")).map((opt) => {
            opt.removeAttribute("selected");
            return opt.cloneNode(true);
        });

        this.countryField = this.el
            .closest("form")
            .querySelector(".s_website_form_input[name='country_id']");
        this.selectedCountryId =
            this.countryField.value || this.countryField.querySelector("[selected]")?.value || "";

        this.availableCountriesIds = Array.from(this.countryField.querySelectorAll("option")).map(
            (opt) => opt.value
        );
    }

    onCountryFieldChange() {
        this.selectedCountryId = this.countryField.value;
    }

    onStateFieldChange() {
        this.selectedStateId = this.el.value;
        if (!this.selectedStateId) {
            return;
        }
        this.selectedCountryId =
            Array.from(this.el.options).find((option) => option.value === this.selectedStateId)
                ?.dataset.countryId || "";
        this.countryField.value = this.selectedCountryId;
    }

    getStateOptions() {
        const optionsToRender = this.allOptions.filter(
            (option) =>
                (!this.selectedCountryId &&
                    this.availableCountriesIds.includes(option.dataset.countryId)) ||
                !option.value ||
                option.dataset.countryId === this.selectedCountryId
        );

        // disable the field if there's no valid option to select
        this.el.disabled = optionsToRender.length <= 1 && !optionsToRender[0]?.value;

        return renderToMarkup(
            "website.form_state_input_field",
            {
                optionsToRender,
                selectedStateId: this.selectedStateId,
            },
            this.el
        );
    }
}

registry.category("public.interactions").add("website.state_form_field", StateFormField);
