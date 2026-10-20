import { Base } from "./base";
import { BACKREF_PREFIX } from "./utils";
import { logPosMessage } from "@point_of_sale/app/utils/pretty_console_log";

const CONSOLE_COLOR = "#FF0000";

/**
 * Collects every record that depends on the given one, recursively.
 *
 * A model depends on another one when it lists it in its `_load_pos_data_dependencies`
 * (e.g. `product.product` depends on `product.template`). Starting from `record`, the
 * relational fields pointing to a dependent model are followed, then the same is done for
 * each record found, so the whole tree below the record is returned.
 *
 * Non-dummy many2one fields are skipped: they are links from the current record to another
 * one, never links from a dependent record to the current one.
 *
 * @param {Base} record - The record
 * @param {Object<string, string[]>} deps - Dependencies by model name
 * @returns {Base[]} The dependent records, without duplicates and without `record` itself.
 */
function getRecordDependencies(record, deps) {
    const result = new Set();
    const stack = [record];

    while (stack.length) {
        const current = stack.pop();
        const model = current.model.name;

        for (const field of Object.values(current.model.fields)) {
            // A non-dummy many2one is a link from the current record, not a link to it
            if (field.type === "many2one" && !field.dummy) {
                continue;
            }
            if (!deps[field.relation]?.includes(model)) {
                continue;
            }

            const value = field.dummy ? current.backLink(field.name) : current[field.name];
            const linkedRecords = Array.isArray(value) ? value : value ? [value] : [];
            for (const linkedRecord of linkedRecords) {
                if (linkedRecord !== record && !result.has(linkedRecord)) {
                    result.add(linkedRecord);
                    stack.push(linkedRecord);
                }
            }
        }
    }

    return [...result];
}

/**
 * Collects every record the given one depends on, recursively.
 *
 * This is the opposite direction of {@link getRecordDependencies}: only the fields of the
 * current record pointing to one of the models listed in its own dependencies are followed.
 * These are the records that must stay loaded for `record` to keep working.
 *
 * @param {Base} record - The record whose requirements are collected.
 * @param {Object<string, string[]>} deps - Dependencies by model name.
 * @returns {Base[]} The required records, without duplicates and without `record` itself.
 */
function getRecordRequirements(record, deps) {
    const result = new Set();
    const stack = [record];

    while (stack.length) {
        const current = stack.pop();
        const dependencies = deps[current.model.name] || [];

        for (const field of Object.values(current.model.fields)) {
            if (field.dummy || !dependencies.includes(field.relation)) {
                continue;
            }

            const value = current[field.name];
            const linkedRecords = Array.isArray(value) ? value : value ? [value] : [];
            for (const linkedRecord of linkedRecords) {
                if (linkedRecord !== record && !result.has(linkedRecord)) {
                    result.add(linkedRecord);
                    stack.push(linkedRecord);
                }
            }
        }
    }

    return [...result];
}

/**
 * Collects every record owned by the given one, recursively.
 *
 * A record owns the children of its non-dummy one2many fields pointing to a dependent model
 * (e.g. the lines and payments of an order). Unlike the records only linked through a dummy
 * back-reference (e.g. the lines of a product), they cannot exist without their owner, so
 * they must stay loaded as long as it does.
 *
 * @param {Base} record - The owner record.
 * @param {Object<string, string[]>} deps - Dependencies by model name.
 * @returns {Base[]} The owned records, without duplicates and without `record` itself.
 */
function getRecordOwnedRecords(record, deps) {
    const result = new Set();
    const stack = [record];

    while (stack.length) {
        const current = stack.pop();
        const model = current.model.name;

        for (const field of Object.values(current.model.fields)) {
            if (field.dummy || field.type !== "one2many") {
                continue;
            }
            if (!deps[field.relation]?.includes(model)) {
                continue;
            }

            for (const linkedRecord of current[field.name] || []) {
                if (linkedRecord !== record && !result.has(linkedRecord)) {
                    result.add(linkedRecord);
                    stack.push(linkedRecord);
                }
            }
        }
    }

    return [...result];
}

/**
 * Collects every record that directly points to the given one, whatever the declared
 * dependencies are.
 *
 * Two kinds of links are considered:
 * - dummy back-reference fields (`<-model.field`), which are the inverse of a many2one or a many2many defined on another model
 * - non-dummy one2many fields, whose children point to the record through the inverse many2one.
 *
 * This is used to keep records that are still referenced by something that is not removed,
 * even if that link is not declared in `_load_pos_data_dependencies`. FIXME: it should be declared there.
 *
 * Fields pointing to one of the record's own dependencies are skipped: the linked records
 * are required by the record, they do not reference it (e.g. the values of an attribute line).
 *
 * Back-references of the fields listed in `ignoredReferences` are skipped too.
 *
 * @param {Base} record - The referenced record.
 * @param {Object<string, string[]>} deps - Dependencies by model name.
 * @param {string[]} ignoredReferences - Fields ("model.field") that do not keep the record.
 * @returns {Base[]} The referring records (may contain duplicates, not recursive).
 */
function getRecordReferrers(record, deps, ignoredReferences) {
    const result = [];
    const requirements = deps[record.model.name] || [];

    for (const field of Object.values(record.model.fields)) {
        if (
            requirements.includes(field.relation) ||
            (field.dummy && ignoredReferences.includes(field.name.slice(BACKREF_PREFIX.length)))
        ) {
            continue;
        }

        let linkedRecords;
        if (field.dummy && field.type !== "many2one") {
            // Inverse of a many2one or a many2many of another model
            linkedRecords = record.backLink(field.name);
        } else if (!field.dummy && field.type === "one2many") {
            // Each child points to the record through the inverse many2one
            linkedRecords = record[field.name];
        }
        if (linkedRecords?.length) {
            result.push(...linkedRecords);
        }
    }

    return result.filter((r) => r instanceof Base);
}

/**
 * Computes the records that can be removed from the PoS because they have not been used
 * recently.
 *
 * Only the models listed in `opts.recordLimits` are limited. For each of them, records are
 * sorted by `uiState.lastUse` and the most recent ones, up to the limit, are kept. Every
 * other record is a candidate for removal, together with its whole tree of dependent records
 * (see {@link getRecordDependencies}).
 *
 * A tree is kept entirely, never partially, as soon as one of its records:
 * - is a kept record, or is required by one (see {@link getRecordRequirements});
 * - is active, meaning its model is in `opts.databaseTable` and its `condition` is false
 * - is referenced by a record that is not removed (see {@link getRecordReferrers}),
 *
 * Keeping a tree only protects its root, the records the root owns (see
 * {@link getRecordOwnedRecords}) and the records they require. The other records of the tree
 * are only linked to the root, which does not need them. They can still be removed by another
 * tree (e.g. the lines of a paid order stay removable even if the template of their product is
 * kept, but not the lines of a kept order). Keeping a root can protect other trees, so the check is repeated until no
 * more tree is kept.
 *
 * @param {Object<string, Model>} models
 * @param {DataServiceOptions} opts
 * @param {Object<string, string[]>} dependencies - Dependencies by model name.
 * @returns {Object<string, Base[]>} The records to remove, grouped by model name.
 */
export function getOutdatedRecords(models, opts, dependencies) {
    // Records kept in indexedDB (e.g. an ongoing order and its lines) are active
    const databaseTable = opts.databaseTable;
    const limitedRecords = opts.recordLimits;
    const candidates = [];
    const required = new Set();
    const recordKey = (record) => `${record.model.name},${record.id}`;
    // A needed record keeps what it requires (e.g. the product of a line) and what it owns
    // (e.g. the lines of an order), with their own requirements
    const requireRecord = (record) => {
        for (const owned of [record, ...getRecordOwnedRecords(record, dependencies)]) {
            required.add(recordKey(owned));
            for (const requirement of getRecordRequirements(owned, dependencies)) {
                required.add(recordKey(requirement));
            }
        }
    };
    const isActive = (record) => {
        const params = databaseTable[record.model.name];
        return Boolean(params && !params.condition(record));
    };

    for (const [model, limit] of Object.entries(limitedRecords)) {
        const records = models[model].getAll();
        if (records.length <= limit) {
            continue;
        }

        const recordsByLastUse = records.sort(
            (a, b) =>
                Boolean(b._outdated) - Boolean(a._outdated) ||
                (b.uiState?.lastUse || 0) - (a.uiState?.lastUse || 0)
        );

        // Isolate the outdated records to remove it even if the limit is not reached
        const outdatedRecords = recordsByLastUse.filter((record) => record._outdated);
        // Records still needed by the kept ones must not be removed
        for (const record of [...outdatedRecords, ...recordsByLastUse.slice(0, limit)]) {
            // for (const record of recordsByLastUse) {
            requireRecord(record);
        }

        // candidates.push(...outdatedRecords, ...recordsByLastUse.slice(limit));
        candidates.push(...recordsByLastUse.slice(limit));
    }

    let trees = candidates.map((record) => [
        record,
        ...getRecordDependencies(record, dependencies),
    ]);

    // Check which trees have active records and mark them as required
    for (const tree of trees) {
        for (const treeRecord of tree) {
            if (isActive(treeRecord)) {
                requireRecord(treeRecord);
            }
        }
    }

    const ignoredReferences = opts.cleanupIgnoredReferences || [];
    const referrersByTree = new Map(
        trees.map((tree) => [
            tree,
            tree
                .flatMap((r) => getRecordReferrers(r, dependencies, ignoredReferences))
                .map(recordKey),
        ])
    );

    // The whole tree is ignored as soon as one of its records is still needed, or is
    // referenced by a record that is kept. Its root then becomes needed, which can
    // protect other trees containing it.
    let changed = true;
    while (changed) {
        changed = false;
        const deletable = new Set(trees.flatMap((tree) => tree.map(recordKey)));
        const remaining = [];
        for (const tree of trees) {
            const isNeeded =
                tree.some((r) => required.has(recordKey(r))) ||
                referrersByTree.get(tree).some((key) => !deletable.has(key));
            if (isNeeded) {
                requireRecord(tree[0]);
                changed = true;
            } else {
                remaining.push(tree);
            }
        }
        trees = remaining;
    }

    const outdated = {};
    const seen = new Set();
    for (const tree of trees) {
        for (const treeRecord of tree) {
            const key = recordKey(treeRecord);
            if (!seen.has(key)) {
                seen.add(key);
                (outdated[treeRecord.model.name] ||= []).push(treeRecord);
            }
        }
    }

    const outdatedModels = Object.keys(outdated);
    if (outdatedModels.length) {
        const outdatedModelsString = outdatedModels.join(", ");
        logPosMessage(
            "cleanup",
            "getOutdatedRecords",
            `Outdated records (models: ${outdatedModelsString})`,
            CONSOLE_COLOR,
            [outdated]
        );
    }

    return outdated;
}
