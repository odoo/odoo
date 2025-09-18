// @ts-check

/** @module @web/model/relational_model/command_builder - x2many ORM command serialization and deduplication (CREATE, UPDATE, LINK, SET, DELETE, UNLINK) */

import { x2ManyCommands } from "@web/services/orm_service";

/**
 * Pure command building and deduplication logic for x2many fields.
 *
 * Extracted from StaticList._getCommands and the deduplication branches
 * of StaticList._applyCommands. These functions have no OWL dependency
 * and can be tested with plain assert.
 *
 * @see static_list.js for the imperative wrapper that calls these
 */

const { CREATE, UPDATE, LINK, SET } = x2ManyCommands;

// ---------------------------------------------------------------------------
// Command serialization
// ---------------------------------------------------------------------------

/**
 * Serialize pending x2many commands into server-ready ORM command tuples.
 *
 * This is the pure core of StaticList._getCommands. Given a list of pending
 * commands and lookup functions for records and unknown commands, produces
 * the final command list to send to the server.
 *
 * @param {Array<[number, string|number, any?]>} commands - pending command list
 * @param {Object} params
 * @param {Object} params.unknownRecordCommands - deferred commands for unloaded records
 * @param {Object} params.fields - field definitions
 * @param {Object} params.activeFields - active field metadata
 * @param {Object} params.context - ORM context
 * @param {boolean} [params.withReadonly] - include readonly fields in values
 * @param {(id: string|number) => Object|undefined} params.getRecord
 *     Lookup a Record datapoint by id from the cache.
 * @param {(record: Object, withReadonly: boolean) => Object} params.getRecordChanges
 *     Get the server-ready changeset from a Record (calls record._getChanges).
 * @param {(values: Object, fields: Object, activeFields: Object, options: Object) => Object} params.convertUnityValues
 *     Convert unity-format values to server format (fromUnityToServerValues).
 * @returns {Array<[number, string|number, any?]>} server-ready command tuples
 */
export function serializeCommands(commands, params) {
    const {
        unknownRecordCommands,
        fields,
        activeFields,
        context,
        withReadonly = false,
        getRecord,
        getRecordChanges,
        convertUnityValues,
    } = params;

    const result = [];

    for (const command of commands) {
        if (command[0] === UPDATE && command[1] in unknownRecordCommands) {
            // Record never loaded — convert deferred unity-format commands
            const uCommands = unknownRecordCommands[command[1]];
            for (const uCommand of uCommands) {
                const values = convertUnityValues(uCommand[2], fields, activeFields, {
                    withReadonly,
                    context,
                });
                result.push([uCommand[0], uCommand[1], values]);
            }
        } else if (command[0] === CREATE || command[0] === UPDATE) {
            const record = getRecord(command[1]);
            if (command[0] === CREATE && record?.resId) {
                // Record was created in x2many dialog and already saved to DB.
                // Replace CREATE with LINK to avoid re-creating.
                result.push([LINK, record.resId]);
            } else {
                const values = getRecordChanges(record, withReadonly);
                // For UPDATE, skip if no actual changes
                if (command[0] === CREATE || Object.keys(values).length) {
                    result.push([command[0], command[1], values]);
                }
            }
        } else {
            // DELETE, UNLINK, LINK, SET, CLEAR — pass through unchanged
            result.push(command);
        }
    }

    return result;
}

// ---------------------------------------------------------------------------
// Command deduplication / cancellation
// ---------------------------------------------------------------------------

/**
 * Determine whether a DELETE command should be emitted for a record,
 * given the existing commands for that record.
 *
 * If the record was CREATEd in this session, DELETE cancels the CREATE
 * (net effect: nothing happened). Otherwise, a DELETE command is emitted.
 *
 * @param {Array<{command: number[], index: number}>} ownCommands
 *     Existing commands for this record id.
 * @returns {boolean} true if a DELETE command should be emitted
 */
export function shouldEmitDelete(ownCommands) {
    const hasCreate = ownCommands.some((x) => x.command[0] === CREATE);
    // Clear all commands for this id regardless
    ownCommands.splice(0);
    return !hasCreate;
}

/**
 * Determine whether an UNLINK command should be emitted for a record,
 * given the existing commands for that record.
 *
 * If the record was LINKed in this session, UNLINK cancels the LINK
 * (net effect: nothing happened). Otherwise, an UNLINK command is emitted.
 *
 * @param {Array<{command: number[], index: number}>} ownCommands
 *     Existing commands for this record id.
 * @returns {boolean} true if an UNLINK command should be emitted
 */
export function shouldEmitUnlink(ownCommands) {
    const linkIndex = ownCommands.findIndex((x) => x.command[0] === LINK);
    if (linkIndex >= 0) {
        ownCommands.splice(linkIndex, 1);
        return false;
    }
    return true;
}

/**
 * Check if an UNLINK should be absorbed by an existing SET command.
 *
 * When a SET command exists as the first command (from _replaceWith),
 * unlinking a record that's in the SET list just removes it from that list
 * rather than emitting a separate UNLINK.
 *
 * @param {Array<[number, any, any?]>} allCommands - the full command list
 * @param {string|number} recordId - the id to unlink
 * @returns {boolean} true if the UNLINK was absorbed by the SET command
 */
export function absorbUnlinkIntoSet(allCommands, recordId) {
    const firstCommand = allCommands[0];
    if (!firstCommand || firstCommand[0] !== SET) {
        return false;
    }
    const ids = firstCommand[2];
    if (!ids.includes(recordId)) {
        return false;
    }
    firstCommand[2] = ids.filter((id) => id !== recordId);
    return true;
}

/**
 * Check whether a duplicate UPDATE command should be skipped.
 *
 * If there's already a CREATE or UPDATE command for this record id,
 * a new UPDATE command is redundant (the record's data will be read
 * from the cache when serializing).
 *
 * @param {Array<{command: number[], index: number}>} ownCommands
 * @returns {boolean} true if the UPDATE is redundant and should be skipped
 */
export function isUpdateRedundant(ownCommands) {
    return ownCommands.some((x) => x.command[0] === CREATE || x.command[0] === UPDATE);
}
