import { serializeDateTime } from "@web/core/l10n/dates";

const simpleSerialization = (record, opts, { X2MANY_TYPES, DATE_TIME_TYPE }) => {
    const orm = opts.orm ?? false;
    const result = {};
    const ownFields = record.model.fields;
    for (const name in ownFields) {
        const field = ownFields[name];
        if ((orm && field.local) || (orm && field.related) || (orm && field.compute)) {
            continue;
        }

        if (field.type === "many2one") {
            result[name] = record[name]?.id || record.raw[name] || false;
        } else if (X2MANY_TYPES.has(field.type)) {
            const ids = [...record[name]].map((record) => record.id);
            result[name] = ids.length ? ids : (!orm && record.raw[name]) || [];
        } else if (DATE_TIME_TYPE.has(field.type) && typeof record[name] === "object") {
            result[name] = serializeDateTime(record[name]);
        } else if (typeof record[name] === "object") {
            result[name] = JSON.stringify(record[name]);
        } else {
            result[name] = record[name] !== undefined ? record[name] : false;
        }
    }
    return result;
};

export const recursiveSerialization = (
    record,
    opts,
    {
        SERIALIZABLE_MODELS,
        X2MANY_TYPES,
        DATE_TIME_TYPE,
        serialized = {},
        uuidMapping = {},
        stack = [],
    }
) => {
    if (!opts.orm) {
        const result = simpleSerialization(record, opts, { X2MANY_TYPES, DATE_TIME_TYPE });
        return { result, uuidMapping };
    }

    const result = {};
    const fields = record.model.fields;
    const recFn = (r) => {
        const { result } = recursiveSerialization(r, opts, {
            SERIALIZABLE_MODELS,
            X2MANY_TYPES,
            DATE_TIME_TYPE,
            serialized,
            uuidMapping,
            stack,
        });
        return result;
    };

    for (const [name, params] of Object.entries(fields)) {
        if (params.local || params.related || params.compute || params.dummy) {
            continue;
        }

        const coModel = params.relation;
        const model = record.model.name;
        const coModelCommands = record.models.commands[coModel];
        const modelCommands = record.models.commands[model];

        if (SERIALIZABLE_MODELS.includes(coModel) && !serialized[coModel]) {
            serialized[coModel] = {};
        }

        if (SERIALIZABLE_MODELS.includes(model) && !serialized[model]) {
            serialized[model] = { [record.uuid]: record.uuid };
        }

        if (!uuidMapping[params.model] && SERIALIZABLE_MODELS.includes(params.model)) {
            uuidMapping[params.model] = {};
        }

        if (X2MANY_TYPES.has(params.type) && record[name]) {
            if (SERIALIZABLE_MODELS.includes(coModel)) {
                const toUpdate = [];
                const toCreate = [];

                for (const r of record[name]) {
                    if (serialized[coModel][r.uuid]) {
                        if (!uuidMapping[params.model][record.uuid]) {
                            uuidMapping[params.model][record.uuid] = {};
                        }

                        if (!uuidMapping[params.model][record.uuid][name]) {
                            uuidMapping[params.model][record.uuid][name] = [];
                        }

                        uuidMapping[params.model][record.uuid][name].push(r.uuid);
                        continue;
                    }

                    if (typeof r.id === "number" && coModelCommands.update.has(r.id)) {
                        toUpdate.push(r);

                        if (opts.clear) {
                            coModelCommands.update.delete(r.id);
                        }
                    } else if (typeof r.id !== "number") {
                        toCreate.push(r);
                    }

                    serialized[coModel][r.uuid] = r.uuid;
                }

                stack.push([
                    result,
                    name,
                    () => [
                        ...(result[name] || []),
                        ...toUpdate.map((r) => [1, r.id, recFn(r)]),
                        ...toCreate.map((r) => [0, 0, recFn(r)]),
                    ],
                ]);
            } else {
                result[name] = record[name].map((record) => record.id);
            }

            if (modelCommands.unlink.has(name) || modelCommands.delete.has(name)) {
                const unlinks = modelCommands.unlink.get(name);
                const deletes = modelCommands.delete.get(name);

                if (!result[name]) {
                    result[name] = [];
                }

                for (const id of unlinks || []) {
                    result[name].push([3, id]);
                }
                for (const id of deletes || []) {
                    result[name].push([2, id]);
                }
                if (opts.clear) {
                    modelCommands.unlink.delete(name);
                    modelCommands.delete.delete(name);
                }
            }

            continue;
        }

        if (params.type === "many2one") {
            if (SERIALIZABLE_MODELS.includes(coModel) && record[name]) {
                if (serialized[coModel][record[name].uuid]) {
                    if (!uuidMapping[params.model][record.uuid]) {
                        uuidMapping[params.model][record.uuid] = {};
                    }

                    uuidMapping[params.model][record.uuid][name] = record[name].uuid;

                    const id = record[name].id;
                    result[name] = typeof id === "number" ? id : parseInt(id.split("_")[1]);
                    continue;
                }

                serialized[coModel][record[name].uuid] = record[name];
                if (coModelCommands.update.has(record[name].id)) {
                    stack.push([result, name, () => [1, record[name].id, recFn(record[name])]]);
                } else {
                    stack.push([result, name, () => [0, 0, recFn(record[name])]]);
                }
            } else if (typeof record[name]?.id === "number") {
                result[name] = record[name] ? record[name].id : false;
            }

            continue;
        }

        if (DATE_TIME_TYPE.has(params.type) && typeof record[name] === "object") {
            result[name] = serializeDateTime(record[name]);
            continue;
        }

        if (name === "id") {
            const id = record[name];
            result[name] = typeof id === "number" ? id : id.split("_")[1];
        } else {
            result[name] = record[name] !== undefined ? record[name] : false;
        }
    }

    while (stack.length) {
        const [res, name, value] = stack.pop();
        res[name] = value();
    }

    return { result, uuidMapping };
};
