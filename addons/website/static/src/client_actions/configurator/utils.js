import { useEnv, useState } from "@odoo/owl";

export const ROUTES = {
    descriptionScreen: 2,
    paletteSelectionScreen: 3,
    featuresSelectionScreen: 4,
    themeSelectionScreen: 5,
    shopPageSelectionScreen: 50,
    productPageSelectionScreen: 55,
};

export function useStore() {
    const env = useEnv();
    return useState(env.store);
}
