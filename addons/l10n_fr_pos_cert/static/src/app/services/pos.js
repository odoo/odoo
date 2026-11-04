import { PosStore } from "@point_of_sale/app/services/pos_store";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { isFrenchCountry } from "@l10n_fr_pos_cert/app/utils";

patch(PosStore.prototype, {
    is_french_country() {
        if (!this.company.country_id) {
            this.dialog.add(AlertDialog, {
                title: _t("Missing Country"),
                body: _t("The company %s doesn't have a country set.", this.company.name),
            });
            return false;
        }
        return isFrenchCountry(this.company);
    },
});
