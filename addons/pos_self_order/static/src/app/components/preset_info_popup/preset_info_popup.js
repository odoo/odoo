import { useState } from "@web/owl2/utils";
import { Component, EventBus, onWillStart } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";
import { Dialog } from "@web/core/dialog/dialog";
import { useAutofocus, useService } from "@web/core/utils/hooks";
import { isValidPhone } from "@point_of_sale/utils";
import { AddressAutoComplete } from "@google_address_autocomplete/address_autocomplete/google_address_autocomplete";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { PillsSelectionPopup } from "@pos_self_order/app/components/pills_selection_popup/pills_selection_popup";
import { _t } from "@web/core/l10n/translation";

class SelfOrderAddressAutoComplete extends AddressAutoComplete {
    setup() {
        super.setup();
        this.selfOrder = useService("self_order");
    }

    get sources() {
        return [
            {
                options: async (partialAddress) => {
                    if (partialAddress.length <= 5) {
                        return [];
                    }
                    const result = await rpc("/pos-self/autocomplete/address", {
                        access_token: this.selfOrder.access_token,
                        partial_address: partialAddress,
                    });
                    return (result.results || []).map((r) => ({
                        label: r.formatted_address,
                        onSelect: () => this.selectAddressProposition(r),
                    }));
                },
                optionSlot: "option",
                placeholder: _t("Searching for addresses..."),
            },
        ];
    }

    async selectAddressProposition(option) {
        const address = await rpc("/pos-self/autocomplete/address_full", {
            access_token: this.selfOrder.access_token,
            address: option.formatted_address,
            google_place_id: option.google_place_id,
        });
        const fieldToDetail = {
            street: "formatted_street_number",
            country_id: "country",
            state_id: "state",
        };
        const fieldsToUpdate = [
            "street",
            "street2",
            "city",
            "state_id",
            "zip",
            "country_id",
            "city_id",
        ];
        const activeFields = this.props.record.activeFields;
        const fields = this.props.record.fields;
        const addressFieldMap = this.props.addressFieldMap;
        const valuesToUpdate = {};
        const rest = [];
        fieldsToUpdate.forEach((fieldName) => {
            const addressField = fieldToDetail[fieldName] || fieldName;
            let value = address[addressField];
            const recordFieldName = addressFieldMap[fieldName] || fieldName;
            if (recordFieldName in activeFields) {
                if (fields[recordFieldName].type === "many2one") {
                    value = value && { id: value[0], display_name: value[1] };
                } else if (Array.isArray(value)) {
                    value = value[1];
                }
                valuesToUpdate[recordFieldName] = value || false;
            } else if (!(recordFieldName in fields) && value) {
                value = Array.isArray(value) ? value[1] : value;
                rest.push(value);
            }
        });
        if (!(this.props.name in valuesToUpdate) && rest.length) {
            valuesToUpdate[this.props.name] = rest.join(" ");
        }
        this.props.record.update(valuesToUpdate);
        await this.props.record.update({ [this.props.name]: option.formatted_address });
    }
}

const { DateTime } = luxon;
export class PresetInfoPopup extends Component {
    static template = "pos_self_order.PresetInfoPopup";
    static components = { Dialog, AddressAutoComplete: SelfOrderAddressAutoComplete };
    static props = {
        close: Function,
        getPayload: Function,
    };

    setup() {
        this.selfOrder = useService("self_order");
        useAutofocus({ mobile: true });
        this.dialog = useService("dialog");

        const partner = this.selfOrder.currentOrder.partner_id;
        const companyStateId = this.selfOrder.config.company_id.country_id.state_ids[0]?.id;
        const companyCountryId = this.selfOrder.config.company_id.country_id.id;

        this.state = useState({
            name: partner?.name || "",
            email: partner?.email || "",
            phoneCode:
                partner?.country_id?.phone_code ||
                this.selfOrder.config.company_id.country_id.phone_code ||
                "",
            phoneLocal: "",
            phoneError: "",
            street: partner?.street || "",
            countryId: partner?.country_id?.id || companyCountryId || null,
            stateId: partner?.state_id?.id || companyStateId || null,
            city: partner?.city || "",
            zip: partner?.zip || "",
            validationError: null,
            isSubmitting: false,
        });
        this.addressRecord = this.makeAddressRecord();

        onWillStart(async () => {
            await this.selfOrder.syncPresetSlotAvaibility(this.preset);
        });
    }

    async setInformations() {
        if (this.state.isSubmitting || !this.checkPhoneFormat()) {
            return;
        }
        this.state.isSubmitting = true;
        this.state.validationError = null;
        try {
            if (this.preset.needsPartner || this.state.phoneLocal) {
                const result = await rpc(`/pos-self-order/validate-partner`, {
                    access_token: this.selfOrder.access_token,
                    preset_id: this.preset?.id,
                    name: this.state.name,
                    email: this.state.email,
                    phone: this.getFullPhone(),
                    street: this.state.street,
                    city: this.state.city,
                    country_id: this.state.countryId,
                    state_id: this.state.stateId,
                    zip: this.state.zip,
                });
                if (this.handleValidationErrors(result)) {
                    return;
                }
                const connectedData = this.selfOrder.models.connectNewData(result);
                this.selfOrder.data.synchronizeServerDataInIndexedDB(result);
                this.setPartnerAndOrderName(connectedData["res.partner"][0]);
                this.selfOrder.currentOrder.partner_id = connectedData["res.partner"][0];
            } else {
                this.selfOrder.currentOrder.floating_order_name = this.state.name;
            }

            this.props.getPayload({ ...this.state, phone: this.getFullPhone() });
            this.props.close();
        } finally {
            this.state.isSubmitting = false;
        }
    }

    handleValidationErrors(result) {
        if (result?.error) {
            this.state.validationError = result.error;
            return true;
        }
        return false;
    }

    setPartnerAndOrderName(partner) {
        if (this.preset.needsPartner) {
            this.selfOrder.currentOrder.floating_order_name = `${this.preset.name} - ${this.state.name}`;
        } else {
            this.selfOrder.currentOrder.floating_order_name = this.state.name;
        }
        this.selfOrder.currentOrder.partner_id = partner;
    }

    makeAddressRecord() {
        const bus = new EventBus();
        const invalidFields = new Set();
        return {
            data: this.state,
            fields: {
                street: { type: "char", trim: false, size: false, translate: false },
                city: { type: "char", trim: false, size: false, translate: false },
                zip: { type: "char", trim: false, size: false, translate: false },
                countryId: { type: "many2one" },
                stateId: { type: "many2one" },
            },
            activeFields: {
                street: true,
                city: true,
                zip: true,
                countryId: true,
                stateId: true,
            },
            model: { bus },
            isValid: true,
            resetFieldValidity: (name) => invalidFields.delete(name),
            setInvalidField: (name) => invalidFields.add(name),
            isFieldInvalid: (name) => invalidFields.has(name),
            update: async (values) => {
                for (const [key, value] of Object.entries(values)) {
                    if (key === "countryId") {
                        this.state.countryId = value?.id || value || null;
                    } else if (key === "stateId") {
                        this.state.stateId = value?.id || value || null;
                    } else {
                        this.state[key] = value || "";
                    }
                }
                this.state.validationError = null;
            },
        };
    }

    get otherPresets() {
        const currentPresetId = this.selfOrder.currentOrder?.preset_id?.id;
        return this.selfOrder.models["pos.preset"].filter((p) => p.id !== currentPresetId);
    }

    async selectPreset(preset) {
        const currentPreset = this.selfOrder.currentOrder?.preset_id;
        // Remove delivery lines when switching away from delivery
        if (currentPreset?.service_at === "delivery") {
            const deliveryProduct = currentPreset.delivery_product_id;
            if (deliveryProduct) {
                const toDelete = this.selfOrder.currentOrder.lines.filter(
                    (l) => l.product_id?.id === deliveryProduct.id
                );
                for (const line of toDelete) {
                    this.selfOrder.removeLine(line);
                }
            }
        }
        this.selfOrder.currentOrder.setPreset(preset);
        this.state.selectedSlot = null;
        this.state.validationError = null;
        await this.selfOrder.syncPresetSlotAvaibility(preset);
        if (preset.needsSlot) {
            const timingOptions = this.selfOrder.getTimingOptions(preset);
            const result = await makeAwaitable(this.dialog, PillsSelectionPopup, {
                options: timingOptions,
                title: _t("Select a hour"),
                subtitle: _t("Please choose a time slot for your order."),
                selectionType: "time",
            });
            if (result) {
                this.selfOrder.currentOrder.preset_time = DateTime.fromSQL(result);
                this.state.selectedSlot = result;
            }
        }
    }

    get addressAutoCompleteProps() {
        return {
            record: this.addressRecord,
            name: "street",
            placeholder: "Address",
            addressFieldMap: {
                street: "street",
                city: "city",
                zip: "zip",
                country_id: "countryId",
                state_id: "stateId",
            },
        };
    }

    close() {
        this.props.close();
    }

    get preset() {
        return this.selfOrder.currentOrder.preset_id;
    }

    get slots() {
        return Object.entries(this.preset.uiState.availabilities).filter(
            (s) => Object.keys(s[1]).length > 0
        );
    }

    get countries() {
        return this.selfOrder.models["res.country"].getAll();
    }

    get states() {
        const country = this.selfOrder.models["res.country"].get(this.state.countryId);
        return country?.state_ids || [];
    }

    get selectedCountry() {
        return this.selfOrder.models["res.country"]
            .getAll()
            .find((c) => c.phone_code === this.state.phoneCode);
    }

    flagEmoji(code) {
        return [...code.toUpperCase()]
            .map((c) => String.fromCodePoint(0x1f1e6 + c.charCodeAt(0) - 65))
            .join("");
    }

    getFullPhone() {
        return this.state.phoneLocal.trim()
            ? `+${this.state.phoneCode}${this.state.phoneLocal.trim()}`
            : "";
    }

    get validSelection() {
        return this.selfOrder.isValidSelection(this.selfOrder.currentOrder.raw.preset_time, {
            id: parseInt(this.state.selectedPartnerId),
            name: this.state.name,
            email: this.state.email,
            phone: this.getFullPhone(),
            street: this.state.street,
            city: this.state.city,
            country_id: this.state.countryId,
            state_id: this.state.stateId,
            zip: this.state.zip,
        });
    }

    formatDate(date) {
        const dateObj = DateTime.fromFormat(date, "yyyy-MM-dd");
        return this.preset.formatDate(dateObj);
    }

    checkPhoneFormat() {
        return !this.state.phoneLocal || isValidPhone(this.getFullPhone());
    }
}
