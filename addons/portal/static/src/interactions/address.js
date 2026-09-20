/** @odoo-module native */
import { makeLogger } from "@web/core/debug/debug_logger";
import { rpc } from "@web/core/network";
import { registry } from "@web/core/registry";
import { redirect } from "@web/core/utils/urls";
import { Interaction } from "@web/public/interaction";

const log = makeLogger("portal.address");

export class CustomerAddress extends Interaction {
    static selector = ".o_customer_address_fill";
    dynamicContent = {
        'select[name="country_id"]': {
            "t-on-change": this.onChangeCountry,
        },
        'select[name="state_id"]': { "t-on-change": this.onChangeState },
        // a form without an endpoint of its own submits natively (the POS invoice
        // request posts to its own controller and only wants the autoformat)
        "form.address_autoformat[data-submit-url]": {
            "t-on-submit.prevent": this.saveAddress,
        },
        "#save_address": { "t-on-click.prevent": this.locked(this.saveAddress, true) },
    };

    setup() {
        this.http = this.services["http"];
        this.addressForm = this.el.querySelector("form.address_autoformat");
        this.errorsDiv = this.el.querySelector("#errors");
        this.addressType = this.addressForm["address_type"].value;
        this.countryCode = this.addressForm.dataset.companyCountryCode;
        this.requiredFields = this.addressForm.required_fields.value.split(",");
        this.requiredFields.forEach((fieldName) => this._markRequired(fieldName, true));
    }

    start() {
        return this._loadCountry(true);
    }

    onChangeCountry() {
        return this._loadCountry();
    }

    _loadCountry(init = false) {
        this.countryChangeFailed = false;
        const countryChange = this._onChangeCountry(init).catch((error) => {
            if (this.countryChange === countryChange) {
                this.countryChangeFailed = true;
                log.logic("country metadata failed; next save can retry");
            }
            throw error;
        });
        this.countryChange = countryChange;
        return countryChange;
    }

    async onChangeState() {}

    async _onChangeCountry(init = false) {
        const request = (this.countryRequest = Symbol());
        const countryId = parseInt(this.addressForm.country_id.value, 10);
        if (!countryId) {
            return;
        }

        const data = await this.waitFor(
            rpc(`/my/address/country_info/${countryId}`, {
                address_type: this.addressType,
            }),
        );

        if (
            request !== this.countryRequest ||
            countryId !== parseInt(this.addressForm.country_id.value, 10)
        ) {
            log.logic("discard stale country response", { countryId });
            return;
        }
        log.logic("apply country response", { countryId });

        if (this.addressForm.phone) {
            this.addressForm.phone.placeholder =
                data.phone_code !== 0 ? `+${data.phone_code}` : "";
        }

        const selectStates = this.addressForm.state_id;
        if (selectStates && (!init || selectStates.options.length === 1)) {
            selectStates.options.length = 1;
            if (data.states.length || data.state_required) {
                data.states.forEach((state) => {
                    const option = new Option(state[1], state[0]);
                    option.setAttribute("data-code", state[2]);
                    selectStates.appendChild(option);
                });
                this._showInput("state_id");
            } else {
                this._hideInput("state_id");
            }
        }

        if (data.fields) {
            const zipDivEl = this._getInputDiv("zip");
            const cityDivEl = this._getInputDiv("city");
            if (zipDivEl && cityDivEl) {
                if (data.zip_before_city) {
                    zipDivEl.after(cityDivEl);
                } else {
                    zipDivEl.before(cityDivEl);
                }
            }

            const all_fields = ["street", "zip", "city"];
            all_fields.forEach((fname) => {
                if (
                    data.fields.includes(fname) ||
                    data.required_fields.includes(fname) ||
                    this.requiredFields.includes(fname)
                ) {
                    this._showInput(fname);
                } else {
                    this._hideInput(fname);
                }
            });
        }

        const required_fields = this.addressForm.querySelectorAll(":required");
        required_fields.forEach((element) => {
            if (
                !data.required_fields.includes(element.name) &&
                !this.requiredFields.includes(element.name)
            ) {
                this._markRequired(element.name, false);
            }
        });
        data.required_fields.forEach((fieldName) => {
            this._markRequired(fieldName, true);
        });
    }

    /**
     * @param {string} name
     * @returns {HTMLElement|null}
     */
    _getInputDiv(name) {
        return this.addressForm[name]?.parentElement ?? null;
    }

    _getInputLabel(name) {
        const input = this.addressForm[name];
        return input?.parentElement?.querySelector(`label[for='${input.id}']`) ?? null;
    }

    _showInput(name) {
        const divEl = this._getInputDiv(name);
        if (divEl) {
            divEl.style.display = "";
        }
    }

    _hideInput(name) {
        const divEl = this._getInputDiv(name);
        if (divEl) {
            divEl.style.display = "none";
        }
    }

    _markRequired(name, required) {
        const input = this.addressForm[name];
        if (input) {
            input.required = required;
        }
        this._getInputLabel(name)?.classList.toggle("label-optional", !required);
    }

    /**
     * @param {Event} ev
     */
    async saveAddress(ev) {
        ev.preventDefault();
        if (this.isSaving) {
            return;
        }

        this.isSaving = true;
        try {
            if (this.countryChangeFailed) {
                this._loadCountry();
            }
            let countryChange;
            do {
                countryChange = this.countryChange;
                try {
                    await countryChange;
                } catch (error) {
                    if (countryChange === this.countryChange) {
                        throw error;
                    }
                    log.logic("ignore obsolete country failure while saving");
                }
            } while (countryChange !== this.countryChange);
            if (!this.addressForm.reportValidity()) {
                return;
            }
            log.logic("submit after country metadata");
            return await this._saveAddress();
        } finally {
            this.isSaving = false;
        }
    }

    async _saveAddress() {
        const result = await this.waitFor(
            this.http.post(
                this.addressForm.dataset.submitUrl,
                new FormData(this.addressForm),
            ),
        );
        if (result.redirectUrl) {
            redirect(result.redirectUrl);
        } else {
            this.el.querySelectorAll(".is-invalid").forEach((element) => {
                if (!result.invalid_fields.includes(element.name)) {
                    element.classList.remove("is-invalid");
                }
            });
            result.invalid_fields.forEach((fieldName) =>
                this.addressForm[fieldName]?.classList.add("is-invalid"),
            );

            const newErrors = result.messages.map((message) => {
                const errorHeader = document.createElement("h5");
                errorHeader.classList.add("text-danger");
                errorHeader.appendChild(document.createTextNode(message));
                return errorHeader;
            });

            this.errorsDiv.replaceChildren(...newErrors);
        }
    }

    _getSelectedCountryCode() {
        const country = this.addressForm.country_id;
        return country.value ? country.selectedOptions[0].getAttribute("code") : "";
    }
}

registry
    .category("public.interactions")
    .add("portal.customer_address", CustomerAddress);
