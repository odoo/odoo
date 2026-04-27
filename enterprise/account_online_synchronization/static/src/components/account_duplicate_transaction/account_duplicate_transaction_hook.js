import { useService } from "@web/core/utils/hooks";
import { useState } from "@odoo/owl";

export function useCheckDuplicateService() {
    return useState(useService("account_online_synchronization.duplicate_check_service"));
}
