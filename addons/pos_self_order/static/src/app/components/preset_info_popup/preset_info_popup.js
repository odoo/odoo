import { useState } from "@web/owl2/utils";
import { Component, onWillStart } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { isValidPhone } from "@point_of_sale/utils";

const { DateTime } = luxon;
export class PresetInfoPopup extends Component {
    static template = "pos_self_order.PresetInfoPopup";
    static components = { Dialog };
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
            phoneError: "",
            street: "",
            countryId: this.selfOrder.config.company_id.country_id.id,
            stateId: this.selfOrder.config.company_id.country_id.state_ids[0]?.id || null,
            city: "",
            zip: "",
        });

        onWillStart(async () => {
            await this.selfOrder.syncPresetSlotAvaibility(this.preset);
        });
    }

    async setInformations() {
        if (this.preset.needsPartner || this.state.phone) {
            const data = {
                access_token: this.selfOrder.access_token,
                name: this.state.name,
                email: this.state.email,
                phone: this.state.phone,
                street: this.state.street,
                city: this.state.city,
                country_id: this.state.countryId,
                state_id: this.state.stateId,
                zip: this.state.zip,
            };
            const result = await rpc(`/pos-self-order/validate-partner`, {
                access_token: this.selfOrder.access_token,
                partner_id: this.state.selectedPartnerId,
                ...data,
            });

            // The endpoint doesn't return private informations
            Object.assign(result["res.partner"][0], data);
            this.selfOrder.data.synchronizeServerDataInIndexedDB(result);

            const partner = this.selfOrder.models.connectNewData(result);
            this.selfOrder.currentOrder.floating_order_name = `${this.preset.name} - ${partner["res.partner"][0].name}`;
            this.selfOrder.currentOrder.partner_id = partner["res.partner"][0];
        } else {
            this.selfOrder.currentOrder.floating_order_name = this.state.name;
        }
        this.props.getPayload(this.state);
        this.props.close();
    }

    selectExistingPartner(event) {
        const partner = this.selfOrder.models["res.partner"].get(event.target.value);
        this.state.name = partner?.name || "";
        this.state.email = partner?.email || "";
        this.state.phone = partner?.phone || "";
        this.state.street = partner?.street || "";
        this.state.city = partner?.city || "";
        this.state.countryId = partner?.country_id?.id || null;
        this.state.stateId = partner?.state_id?.id || null;
        this.state.zip = partner?.zip || "";
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

    get countries() {
        return this.selfOrder.models["res.country"].getAll();
    }

    get states() {
        const country = this.selfOrder.models["res.country"].get(this.state.countryId);
        return country?.state_ids || [];
    }

    get validSelection() {
        return this.selfOrder.isValidSelection(this.selfOrder.currentOrder.raw.preset_time, {
            id: parseInt(this.state.selectedPartnerId),
            name: this.state.name,
            email: this.state.email,
            phone: this.state.phone,
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
        return !this.state.phone || isValidPhone(this.state.phone);
    }
}
