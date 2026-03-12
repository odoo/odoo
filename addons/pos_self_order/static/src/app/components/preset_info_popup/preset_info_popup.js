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

        const partner = this.selfOrder.currentOrder.partner_id;
        const companyStateId = this.selfOrder.config.company_id.country_id.state_ids[0]?.id;
        const companyCountryId = this.selfOrder.config.company_id.country_id.id;

        this.state = useState({
            selectedPartnerId: partner?.id || null,
            name: partner?.name || "",
            email: partner?.email || "",
            phone: partner?.phone || "",
            phoneError: "",
            street: partner?.street || "",
            countryId: partner?.country_id?.id || companyCountryId || null,
            stateId: partner?.state_id?.id || companyStateId || null,
            city: partner?.city || "",
            zip: partner?.zip || "",
        });

        onWillStart(async () => {
            await this.selfOrder.syncPresetSlotAvaibility(this.preset);
        });
    }

    async setInformations() {
        if (this.preset.needsPartner || this.state.phone) {
            const countryId = parseInt(this.state.countryId, 10) || null;
            const stateId = parseInt(this.state.stateId, 10) || null;
            const partnerData = {
                name: this.state.name,
                email: this.state.email,
                phone: this.state.phone,
                street: this.state.street,
                city: this.state.city,
                country_id: countryId,
                state_id: stateId,
                zip: this.state.zip,
            };
            const result = await rpc(`/pos-self-order/validate-partner`, {
                access_token: this.selfOrder.access_token,
                partner_id: this.state.selectedPartnerId,
                ...partnerData,
            });

            const partnerId = result?.["res.partner"]?.[0]?.id;
            if (!partnerId) {
                return;
            }
            // The endpoint doesn't return private informations
            partnerData.id = partnerId;
            result["res.partner"][0] = partnerData;
            this.selfOrder.data.synchronizeServerDataInIndexedDB(result);
            const connectedData = this.selfOrder.models.connectNewData(result);
            const partner = connectedData["res.partner"][0];
            this.selfOrder.currentOrder.floating_order_name = `${this.preset.name} - ${partner.name}`;
            this.selfOrder.currentOrder.partner_id = partner;
        } else {
            this.selfOrder.currentOrder.floating_order_name = this.state.name;
        }
        this.props.getPayload(this.state);
        this.props.close();
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
