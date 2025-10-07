import { patch } from "@web/core/utils/patch";
import { GenericHooks } from "@point_of_sale/../tests/pos/tours/utils/generic_hooks";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";

patch(GenericHooks, {
    afterValidateHook(...args) {
        const params = new URLSearchParams(document.location.search);
        const company_name = params.get("company_name");
        if (company_name == "Generic SA EDI") {
            return [Dialog.confirm()];
        } else {
            return super.afterValidateHook(...args);
        }
    },
});
