import { serializeDateTime, serializeDate } from "@web/core/l10n/dates";
import { X2MANY_TYPES, DATE_TIME_TYPE } from "./utils";

const deepSerialization = (
    record,
    opts,
    {
        serialized = {},
        uuidMapping = {},
        parentRelInverseName = null,
        stack = [],
        recordDependencies = {},
    }
) => {
    const result = {};
    const { fields, name: currentModel } = record.model;
    const DYNAMIC_MODELS = opts.dynamicModels;
    const recursiveSerialize = (childRecord, parentRelInverseName) =>
        deepSerialization(childRecord, opts, {
            serialized,
            uuidMapping,
            parentRelInverseName,
            stack,
            recordDependencies,
        });

    // We only care about the fields present in python model
    for (const [fieldName, field] of Object.entries(fields)) {
        if (field.local || field.related || field.compute || field.dummy) {
            continue;
        }

        const relatedModel = field.relation;
        const targetModel = field.model;
        const modelCommands = record.models.commands[currentModel];

        if (relatedModel) {
            if (!record.models[relatedModel]) {
                // Ignore not "loaded" model
                continue;
            }

            if (DYNAMIC_MODELS.includes(relatedModel) && !serialized[relatedModel]) {
                serialized[relatedModel] = {};
            }
        }
        if (DYNAMIC_MODELS.includes(currentModel) && !serialized[currentModel]) {
            serialized[currentModel] = { [record.uuid]: record.uuid };
        }
        if (DYNAMIC_MODELS.includes(targetModel) && !uuidMapping[targetModel]) {
            uuidMapping[targetModel] = {};
        }
        if (X2MANY_TYPES.has(field.type) && record[fieldName]) {
            if (fieldName === "child_prep_line_ids") {
                //create the prep_line and prep_order before original order is created
                continue;
            }
            if (opts.disableRecursive) {
                if (opts.dynamicModels.includes(field.relation)) {
                    uuidMapping[targetModel][record.uuid] ??= {};
                    uuidMapping[targetModel][record.uuid][fieldName] = record[fieldName].map(
                        (childRecord) => childRecord.uuid
                    );
                }

                continue;
            }

            if (DYNAMIC_MODELS.includes(relatedModel)) {
                const toUpdate = [];
                const toCreate = [];

                for (const childRecord of record[fieldName]) {
                    if (serialized[relatedModel][childRecord.uuid]) {
                        continue;
                    }

                    if (typeof childRecord.id === "number" && childRecord._dirty) {
                        toUpdate.push(childRecord);

                        if (!opts.keepCommands) {
                            childRecord.unmarkDirty();
                        }
                    } else if (typeof childRecord.id !== "number") {
                        toCreate.push(childRecord);
                    }
                    serialized[relatedModel][childRecord.uuid] = childRecord.uuid;
                }
                // The stack defers processing of x2many relationships to ensure objects are only serialized
                // once in their first encountered parent, preventing redundant serialization.
                stack.push([
                    result,
                    fieldName,
                    () => [
                        ...(result[fieldName] || []),
                        ...toUpdate.flatMap((childRecord) => [
                            [
                                1,
                                childRecord.id,
                                recursiveSerialize(childRecord, field.inverse_name),
                            ],
                            [4, childRecord.id], // Ensure relationship after editing a record, this can be usefull when splitting orders
                        ]),
                        ...toCreate.map((childRecord) => [
                            0,
                            0,
                            recursiveSerialize(childRecord, field.inverse_name),
                        ]),
                    ],
                ]);
            } else {
                result[fieldName] = record[fieldName]
                    .filter((childRecord) => childRecord.id)
                    .map((childRecord) => {
                        if (typeof childRecord.id !== "number") {
                            throw new Error(
                                `Trying to create a non serializable record '${relatedModel}'`
                            );
                        }
                        return childRecord.id;
                    });
            }

            if (modelCommands.unlink.has(fieldName) || modelCommands.delete.has(fieldName)) {
                result[fieldName] = result[fieldName] || [];
                const processRecords = (records, cmdCode) => {
                    for (const { id, parentId } of records) {
                        const isAlreadyDeleted = serialized[relatedModel]?.["_deleted_" + id];
                        if (parentId === record.id && !isAlreadyDeleted) {
                            const isCascadeDelete =
                                record.models[relatedModel]?.fields[field.inverse_name]?.ondelete;
                            if (isCascadeDelete) {
                                serialized[relatedModel]["_deleted_" + id] = true;
                            }
                            result[fieldName].push([cmdCode, id]);
                        }
                    }
                };
                processRecords(modelCommands.unlink.get(fieldName) || [], 3);
                processRecords(modelCommands.delete.get(fieldName) || [], 2);

                for (const commands of [modelCommands.unlink, modelCommands.delete]) {
                    const commandList = commands.get(fieldName) || [];
                    const remainingCommands = commandList.filter(
                        ({ parentId }) => parentId !== record.id
                    );

                    if (opts.keepCommands) {
                        continue;
                    }

                    if (remainingCommands.length) {
                        commands.set(fieldName, remainingCommands);
                    } else {
                        commands.delete(fieldName);
                    }
                }
            }
            continue;
        }

        if (field.type === "many2one") {
            const recordId = record[fieldName]?.id;
            if (DYNAMIC_MODELS.includes(relatedModel) && record[fieldName]) {
                if (
                    fieldName !== parentRelInverseName && //mapping not needed for direct child
                    record.uuid &&
                    !recordDependencies[field.relation]?.[record[fieldName].uuid]
                ) {
                    //check if pos.order.line since synched with orderline in dependencies
                    //when unmerging
                    if (
                        !serialized[relatedModel][recordId] &&
                        record[fieldName]._dirty &&
                        field.relation != "pos.order.line"
                    ) {
                        const relatedUUID = record[fieldName].uuid;
                        recordDependencies[field.relation] ??= {};
                        recordDependencies[field.relation][relatedUUID] ??= {
                            create: [],
                            update: [],
                        };
                        const serializedRecords = () =>
                            deepSerialization(
                                record[fieldName],
                                {
                                    ...opts,
                                    disableRecursive: true,
                                },
                                { uuidMapping, serialized }
                            );
                        if (typeof recordId !== "number") {
                            recordDependencies[field.relation][relatedUUID]["create"].push(
                                serializedRecords
                            );
                            record[fieldName].unmarkDirty();
                        } else if (typeof recordId === "number" && record[fieldName]._dirty) {
                            recordDependencies[field.relation][relatedUUID]["update"].push(
                                serializedRecords
                            );
                        }
                    }
                    uuidMapping[targetModel][record.uuid] ??= {};
                    uuidMapping[targetModel][record.uuid][fieldName] = record[fieldName].uuid;
                }
                serialized[relatedModel][record[fieldName].uuid] = record[fieldName].uuid;
            }
            if (typeof recordId === "number" && recordId >= 0) {
                result[fieldName] = recordId;
            } else if (record[fieldName] === undefined) {
                result[fieldName] = false;
            }
            continue;
        }
        if (DATE_TIME_TYPE.has(field.type) && typeof record[fieldName] === "object") {
            result[fieldName] =
                field.type === "datetime"
                    ? serializeDateTime(record[fieldName])
                    : serializeDate(record[fieldName]);
            continue;
        }
        if (fieldName === "id") {
            if (typeof record[fieldName] === "number") {
                result[fieldName] = record[fieldName];
            }
            continue;
        }
        result[fieldName] = record[fieldName] !== undefined ? record[fieldName] : false;
    }

    while (stack.length) {
        const [res, key, getValue] = stack.pop();
        res[key] = getValue();
    }

    if (!opts.keepCommands) {
        record.unmarkDirty();
    }

    // Cleanup: remove empty entries from uuidMapping.
    for (const key in uuidMapping) {
        if (
            uuidMapping[key] &&
            typeof uuidMapping[key] === "object" &&
            Object.keys(uuidMapping[key]).length === 0
        ) {
            delete uuidMapping[key];
        }
    }

    return result;
};

export const ormSerialization = (record, opts) => {
    const serialized = {};
    const uuidMapping = {};
    const recordDependencies = {};
    const result = deepSerialization(record, opts, {
        serialized,
        uuidMapping,
        recordDependencies,
    });

    if (Object.keys(uuidMapping).length !== 0) {
        result.relations_uuid_mapping = uuidMapping;
    }

    if (Object.keys(recordDependencies).length !== 0) {
        const normalizedDependencies = {};

        for (const modelName in recordDependencies) {
            const create = [];
            const update = [];

            for (const deps of Object.values(recordDependencies[modelName])) {
                deps.create?.length && create.push(...deps.create.map((f) => f()).filter(Boolean));
                deps.update?.length && update.push(...deps.update.map((f) => f()).filter(Boolean));
            }

            if (create.length || update.length) {
                normalizedDependencies[modelName] = {
                    ...(create.length && { create: create }),
                    ...(update.length && { update: update }),
                };
            }
        }
        result.record_dependencies = normalizedDependencies;
    }

    return result;
};
