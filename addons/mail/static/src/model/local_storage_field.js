import { makeRecordFieldLocalId } from "@mail/model/misc";

import {
    LocalStorageEntry,
    parseRawValue,
    subscribeToStorage,
} from "@mail/utils/common/local_storage";

/**
 * Implements `Record.localStorage()`: the marker it returns identifies the field
 * once the record is constructed, and the value then follows the storage entry.
 *
 * @template T
 * @param {import("./record").Record} record
 * @param {T} [defaultValue]
 * @returns {T}
 */
export function localStorageField(record, defaultValue) {
    const marker = { localStorageField };
    let ls;
    let fieldName;
    let applyingStorageEvent = false;
    record.onChange(
        () => [], // one-shot at construction release: the localId is assigned
        () => {
            fieldName = [...record._.fieldsSignal].find(([, sig]) => sig() === marker)?.[0];
            if (!fieldName) {
                throw new Error("localStorage() return value must be assigned to the field");
            }
            ls = new LocalStorageEntry(makeRecordFieldLocalId(record.localId, fieldName));
            const stored = ls.get();
            if (stored === undefined || stored === defaultValue) {
                ls.remove();
                record[fieldName] = defaultValue;
            } else {
                record[fieldName] = stored;
            }
            return subscribeToStorage(ls.key, (ev) => {
                applyingStorageEvent = true;
                try {
                    const parsed = ev.newValue === null ? undefined : parseRawValue(ev.newValue);
                    record[fieldName] = parsed ? parsed.value : defaultValue;
                } finally {
                    applyingStorageEvent = false;
                }
            });
        },
        { immediate: true }
    );
    record.onChange(
        () => [fieldName && record[fieldName]],
        (value) => {
            if (applyingStorageEvent || !ls) {
                return;
            }
            if (value === defaultValue) {
                ls.remove();
            } else {
                ls.set(value);
            }
        },
        { immediate: true, initialRun: false }
    );
    return /** @type {T} */ (marker);
}
