// @ts-check
/** @odoo-module native */

import { modelLog } from "@web/core/utils/asset_log";

/** @import { RelationalRecord } from "@web/model/relational_model/record" */

/**
 * @param {RelationalRecord} record
 * @param {() => Promise<any>} [reload]
 * @returns {Promise<any>}
 */
export async function archive(record, reload) {
    modelLog("archive", record.resModel, record.resId);
    return toggleArchive(record, true, reload);
}

/**
 * @param {RelationalRecord} record
 * @param {() => Promise<any>} [reload]
 * @returns {Promise<any>}
 */
export async function unarchive(record, reload) {
    modelLog("unarchive", record.resModel, record.resId);
    return toggleArchive(record, false, reload);
}

/**
 * @param {RelationalRecord} record
 * @param {boolean} state
 * @returns {Promise<any>}
 */
async function toggleArchive(record, state, reload = () => record.loadLocked()) {
    const method = state ? "action_archive" : "action_unarchive";
    const action = await record.model.orm.call(
        record.resModel,
        method,
        [[record.resId]],
        {
            context: record.context,
        },
    );
    return record.model.uiHooks.onDisplayArchiveAction(action, reload);
}

/**
 * @param {RelationalRecord} record
 * @returns {Promise<boolean | undefined>}
 */
export async function deleteRecord(record) {
    modelLog("delete", record.resModel, record.resId);
    const unlinked = await record.model.orm.unlink(record.resModel, [record.resId], {
        context: record.context,
    });
    if (!unlinked) {
        return false;
    }
    const resIds = [...(record.resIds ?? [])];
    const index = resIds.indexOf(/** @type {number} */ (record.resId));
    if (index >= 0) {
        resIds.splice(index, 1);
    }
    const resId = resIds[Math.min(Math.max(index, 0), resIds.length - 1)] || false;
    if (resId) {
        await record.model.load({ resId, resIds });
    } else {
        record.model.patchConfig(record.config, { resId: false, resIds });
        record.resetValues(record.parseServerValues(record.getDefaultValues()));
    }
}

/**
 * @param {RelationalRecord} record
 * @returns {Promise<void>}
 */
export async function duplicateRecord(record) {
    modelLog("duplicate", record.resModel, record.resId);
    const kwargs = { context: record.context };
    const currentResIds = record.resIds ?? [];
    const index = currentResIds.indexOf(/** @type {number} */ (record.resId));
    const [resId] = await record.model.orm.call(
        record.resModel,
        "copy",
        [[record.resId]],
        kwargs,
    );
    const resIds = [...currentResIds];
    resIds.splice(index + 1, 0, resId);
    await record.model.load({ resId, resIds, mode: "edit" });
}
