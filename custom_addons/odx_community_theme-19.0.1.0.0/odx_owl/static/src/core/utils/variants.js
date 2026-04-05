/** @odoo-module **/

import { cn } from "@odx_owl/core/utils/cn";

export function cva(base, config = {}) {
    const { variants = {}, defaultVariants = {}, compoundVariants = [] } = config;

    return (options = {}) => {
        const classes = [base];
        for (const [variantName, variantMap] of Object.entries(variants)) {
            const value = options[variantName] ?? defaultVariants[variantName];
            if (value && variantMap[value]) {
                classes.push(variantMap[value]);
            }
        }
        for (const compound of compoundVariants) {
            let matches = true;
            for (const [key, value] of Object.entries(compound)) {
                if (key === "className") {
                    continue;
                }
                if ((options[key] ?? defaultVariants[key]) !== value) {
                    matches = false;
                    break;
                }
            }
            if (matches && compound.className) {
                classes.push(compound.className);
            }
        }
        if (options.className) {
            classes.push(options.className);
        }
        return cn(classes);
    };
}
