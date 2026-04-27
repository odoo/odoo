/** @odoo-module */

import { deserializeDateTime } from "@web/core/l10n/dates";

const { DateTime } = luxon;

export function formatToLocaleString(ISOdatetime, code) {
    return deserializeDateTime(ISOdatetime).setLocale(code).toLocaleString(DateTime.DATETIME_MED);
}

export function addToRegistryWithCleanup(cleanUpHook, registry, name, item) {
    registry.add(name, item);
    cleanUpHook(() => {
        registry.remove(name);
    });
}
