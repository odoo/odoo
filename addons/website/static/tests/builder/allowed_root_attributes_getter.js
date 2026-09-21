import { globals } from "@odoo/hoot";

let allowedRootAttrs;
export const getAllowedRootAttrs = async () => {
    if (!allowedRootAttrs) {
        allowedRootAttrs = globals
            .fetch("/website/get_allowed_root_attrs", {
                body: JSON.stringify({}),
                headers: { "Content-Type": "application/json" },
                method: "POST",
            })
            .then(async (response) => {
                const { error, result } = await response.json();
                if (error) {
                    throw error;
                }
                return result;
            });
    }
    return allowedRootAttrs;
};