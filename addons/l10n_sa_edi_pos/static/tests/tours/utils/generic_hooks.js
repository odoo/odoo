import { patch } from "@web/core/utils/patch";
import { GenericHooks } from "@point_of_sale/../tests/tours/utils/generic_hooks";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import { session } from "@web/session";

patch(GenericHooks, {
    afterValidateHook(...args) {
        const company_name =
            session.user_companies.allowed_companies[session.user_companies.current_company].name;
        if (company_name == "Generic SA EDI") {
            return [Dialog.confirm()];
        } else {
            return super.afterValidateHook(...args);
        }
    },
});
