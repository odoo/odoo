import { Component, onWillStart, useState } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/services/self_order_service";
import { rpc } from "@web/core/network/rpc";
import { localization } from "@web/core/l10n/localization";
import { isValidEmail } from "@point_of_sale/utils";

const { DateTime } = luxon;
export class PresetInfoPopup extends Component {
    static template = "pos_self_order.PresetInfoPopup";
    static props = { callback: Function };

    setup() {
        this.selfOrder = useSelfOrder();
        const partner = this.selfOrder.currentOrder.partner_id;
        const companyStateId = this.selfOrder.config.company_id.country_id.state_ids[0]?.id;
        const companyCountryId = this.selfOrder.config.company_id.country_id.id;

        this.state = useState({
            selectedSlot: null,
            selectedPartnerId: partner?.id || null,
            name: partner?.name || "",
            email: partner?.email || "",
            phone: partner?.phone || "",
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
        if (this.preset.needsPartner) {
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
            partnerData.id = partnerId;
            result["res.partner"][0] = partnerData;
            const connectedData = this.selfOrder.models.connectNewData(result);
            const partner = connectedData["res.partner"][0];
            partner.pos_contact_address =
                partner.street +
                "\n" +
                [partner.city, partner.state_id?.code, partner.zip].filter(Boolean).join(" ") +
                "\n" +
                (partner.country_id?.name || "");
            this.selfOrder.currentOrder.floating_order_name = `${this.preset.name} - ${partner.name}`;
            this.selfOrder.currentOrder.partner_id = partner;
        } else {
            this.selfOrder.currentOrder.floating_order_name = this.state.name;
        }

        if (this.preset.needsSlot && this.state.selectedSlot) {
            this.selfOrder.currentOrder.preset_time = DateTime.fromSQL(this.state.selectedSlot)
                .toUTC()
                .toFormat("yyyy-MM-dd HH:mm:ss");
        }

        this.props.callback(this.state);
    }

    // TODO: remove in master
    selectExistingPartner(event) {}

    // TODO: remove in master
    get existingPartners() {
        return this.selfOrder.models["res.partner"].getAll();
    }

    // TODO: remove in master
    get partnerIsSelected() {
        return false;
    }

    close() {
        this.props.callback(false);
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
        const partnerInfo =
            this.state.name &&
            this.state.phone &&
            this.state.street &&
            this.state.city &&
            this.state.countryId &&
            (this.state.stateId || !this.states.length) &&
            this.state.zip;
        return (
            (!this.preset.needsSlot || DateTime.fromSQL(this.state.selectedSlot).isValid) &&
            (!this.preset.needsName || this.state.name) &&
            (!this.preset.needsEmail || isValidEmail(this.state.email)) &&
            (!this.preset.needsPartner || partnerInfo)
        );
    }

    formatDate(date) {
        const dateObj = DateTime.fromFormat(date, "yyyy-MM-dd");
        return dateObj.toFormat(localization.dateFormat);
    }
}
