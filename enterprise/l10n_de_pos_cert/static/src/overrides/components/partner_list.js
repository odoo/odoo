import { _t } from "@web/core/l10n/translation";
import { PartnerList } from "@point_of_sale/app/screens/partner_list/partner_list";
import { patch } from "@web/core/utils/patch";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

patch(PartnerList.prototype, {
    clickPartner(partner) {
        if (
            partner &&
            this.pos.isCountryGermanyAndFiskaly() &&
            !(partner.street?.length > 1 && partner.zip?.length > 1)
        ) {
            return this.dialog.add(AlertDialog, {
                title: _t("Invalid/Missing field(s) data"),
                body: _t(
                    "Please make sure the selected customer has the following required details filled in before proceeding:\n- Street Address\n- Zip Code\nYou can update these in the customer’s profile."
                ),
            });
        }
        return super.clickPartner(partner);
    },
});
