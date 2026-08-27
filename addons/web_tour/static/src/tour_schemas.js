import { t } from "@odoo/owl";

export const tourSchema = {
    steps: t.function(),
};

const stepSchema = {
    trigger: t.string(),
    id: t.string().optional(),
    isActive: t.array(t.string()).optional(),
    run: t
        .customValidator(
            t.or([t.string(), t.function()]),
            (fn) => typeof fn === "string" || !/\{\s*\}$/.test(fn.toString().trim()),
            "run must be a string or a non-empty function"
        )
        .optional(),
};

export const stepSchemaAuto = {
    ...stepSchema,
    content: t.string().optional(),
    expectUnloadPage: t.boolean().optional(),
    timeout: t.customValidator(t.number(), (value) => value >= 0 && value <= 60000).optional(),
    tooltipPosition: t
        .customValidator(t.string(), (value) => ["top", "bottom", "left", "right"].includes(value))
        .optional(),
};

export const stepSchemaDebugAuto = {
    ...stepSchemaAuto,
    pause: t.boolean().optional(),
    break: t.boolean().optional(),
};

export const stepSchemaOnboarding = {
    ...stepSchema,
    content: t.or([t.string(), t.object()]).optional(), //allow object(_t && markup)
    tooltipPosition: t
        .customValidator(t.string(), (value) => ["top", "bottom", "left", "right"].includes(value))
        .optional(),
};

export const stepSchemaDebugOnboarding = {
    ...stepSchemaOnboarding,
    pause: t.boolean().optional(),
    break: t.boolean().optional(),
};
