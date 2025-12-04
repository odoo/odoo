import { globals } from "@odoo/hoot";

let translatedElements;
export const getTranslatedElements = async () => {
    if (!translatedElements) {
        translatedElements = globals
            .fetch("/website/get_translated_elements", {
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
    return translatedElements;
};
