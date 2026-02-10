import { Component, onWillStart, useState, EventBus } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";
import { isValidEmail } from "@point_of_sale/utils";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { AddressAutoComplete } from "@google_address_autocomplete/address_autocomplete/google_address_autocomplete";

const { DateTime } = luxon;
export class PresetInfoPopup extends Component {
    static template = "pos_self_order.PresetInfoPopup";
    static components = { Dialog, AddressAutoComplete };
    static props = {
        close: Function,
        getPayload: Function,
    };

    setup() {
        this.selfOrder = useService("self_order");
        this.state = useState({
            selectedPartnerId: null,
            name: "",
            email: "",
            phone: "",
            street: "",
            city: "",
            zip: "",
            countryId: this.selfOrder.config.company_id.country_id.id,
            stateId: this.selfOrder.config.company_id.country_id.state_ids[0]?.id || null,
            validationError: null,
            isSubmitting: false,
        });
        this.addressRecord = this.makeAddressRecord();

        onWillStart(async () => {
            await this.selfOrder.syncPresetSlotAvaibility(this.preset);
        });
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
            this.selfOrder.currentOrder.floating_order_name = `${this.preset.name} - ${partner["res.partner"][0].name}`;
        } else {
            this.selfOrder.currentOrder.floating_order_name = partner["res.partner"][0].name;
        }
        this.selfOrder.currentOrder.partner_id = partner["res.partner"][0];
    }

    async setInformations() {
        if (this.state.isSubmitting || !this.checkPhoneFormat()) {
            return;
        }
        this.state.isSubmitting = true;
        this.state.validationError = null;
        try {
            if (this.preset.needsPartner || this.state.phone) {
                const result = await rpc(`/pos-self-order/validate-partner`, {
                    access_token: this.selfOrder.access_token,
                    partner_id: this.state.selectedPartnerId,
                    preset_id: this.preset?.id,
                    name: this.state.name,
                    email: this.state.email,
                    phone: this.state.phone,
                    street: this.state.street,
                    city: this.state.city,
                    country_id: this.state.countryId,
                    state_id: this.state.stateId,
                    zip: this.state.zip,
                });
                if (this.handleValidationErrors(result)) {
                    return;
                }
                const partner = this.selfOrder.models.connectNewData(result);
                this.setPartnerAndOrderName(partner);
            } else {
                this.selfOrder.currentOrder.floating_order_name = this.state.name;
            }

            if (this.preset.needsSlot && this.state.selectedSlot) {
                this.selfOrder.currentOrder.preset_time = DateTime.fromSQL(this.state.selectedSlot)
                    .toUTC()
                    .toFormat("yyyy-MM-dd HH:mm:ss");
            }
            this.props.getPayload(this.state);
            this.props.close();
        } finally {
            this.state.isSubmitting = false;
        }
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

    get takeoutPreset() {
        const presets = this.selfOrder.models["pos.preset"].getAll();
        return presets.find((preset) => preset.service_at === "counter") || null;
    }

    async selectTakeoutPreset() {
        const preset = this.takeoutPreset;
        if (!preset) {
            return;
        }
        this.selfOrder.currentOrder.setPreset(preset);
        await this.selfOrder.ensureDeliveryLine(preset.service_at);
        this.state.selectedSlot = null;
        this.state.validationError = null;
        await this.selfOrder.syncPresetSlotAvaibility(preset);
    }

    get addressAutoCompleteProps() {
        return {
            record: this.addressRecord,
            name: "street",
            placeholder: "Address",
            readonly: Boolean(this.partnerIsSelected),
            addressFieldMap: {
                street: "street",
                city: "city",
                zip: "zip",
                country_id: "countryId",
                state_id: "stateId",
            },
        };
    }

    selectExistingPartner(event) {
        const partner = this.selfOrder.models["res.partner"].get(event.target.value);
        this.state.name = partner?.name || "";
        this.state.email = partner?.email || "";
        this.state.phone = partner?.phone || "";
        this.state.street = partner?.street || "";
        this.state.city = partner?.city || "";
        this.state.zip = partner?.zip || "";
        this.state.countryId = partner?.country_id?.id || null;
        this.state.stateId = partner?.state_id?.id || null;
        this.state.validationError = null;
    }

    get existingPartners() {
        return this.selfOrder.models["res.partner"].getAll();
    }

    get partnerIsSelected() {
        return this.state.selectedPartnerId && this.state.selectedPartnerId !== "0";
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

    get validSelection() {
        const partnerInfo = this.state.name && this.state.phone && this.state.street;
        return (
            (!this.preset.needsName || this.state.name) &&
            (!this.preset.needsEmail || isValidEmail(this.state.email)) &&
            (!this.preset.needsPartner || partnerInfo) &&
            !this.state.validationError &&
            this.checkPhoneFormat()
        );
    }

    formatDate(date) {
        const dateObj = DateTime.fromFormat(date, "yyyy-MM-dd");
        return this.preset.formatDate(dateObj);
    }

    checkPhoneFormat() {
        if (!this.state.phone) {
            return true;
        }
        const phone = this.state.phone.replace(/[\s.\-()]/g, "");
        const pattern = /^\+\d{8,18}$/;
        return pattern.test(phone);
    }
}
