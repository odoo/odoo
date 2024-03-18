import { reactive, useState } from "@odoo/owl";

export const features = reactive({
    advanced: !!odoo.debug,
});

export function useFeatures() {
    return useState(features);
}
