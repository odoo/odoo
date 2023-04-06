/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { onWillStart } from "@odoo/owl";

export function useAccessRights(model, permission) {
    const result = {};
    const userService = useService("user");
    onWillStart(async () => {
        result.value = await userService.checkAccessRight(model, permission);
    });
    return result;
}
