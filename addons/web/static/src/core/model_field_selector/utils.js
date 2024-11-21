import { useService } from "@web/core/utils/hooks";

function makeString(value) {
    return String(value ?? "-");
}

export function useLoadFieldInfo(fieldService) {
    fieldService ||= useService("field");
    return async (resModel, path) => {
        if (typeof path !== "string" || !path) {
            return { resModel, fieldDef: null };
        }
        const { isInvalid, names, modelsInfo } = await fieldService.loadPath(resModel, path);
        if (isInvalid) {
            return { resModel, fieldDef: null };
        }
        const name = names.at(-1);
        const modelInfo = modelsInfo.at(-1);
        return { resModel: modelInfo.resModel, fieldDef: modelInfo.fieldDefs[name] };
    };
}

export function useLoadPathDescription(fieldService) {
    fieldService ||= useService("field");
    return async (resModel, path, allowEmpty) => {
        if ([0, 1].includes(path)) {
            return { isInvalid: false, displayNames: [makeString(path)] };
        }
        if (allowEmpty && !path) {
            return { isInvalid: false, displayNames: [] };
        }
        if (typeof path !== "string" || !path) {
            return { isInvalid: true, displayNames: [makeString()] };
        }
        const { isInvalid, modelsInfo, names } = await fieldService.loadPath(resModel, path);
        const result = { isInvalid: !!isInvalid, displayNames: [] };
        if (!isInvalid) {
            const lastName = names.at(-1);
            const lastFieldDef = modelsInfo.at(-1).fieldDefs[lastName];
            if (["properties", "properties_definition"].includes(lastFieldDef.type)) {
                // there is no known case where we want to select a 'properties' field directly
                result.isInvalid = true;
            }
        }
        for (let index = 0; index < names.length; index++) {
            const name = names[index];
            const fieldDef = modelsInfo[index]?.fieldDefs[name];
            result.displayNames.push(fieldDef?.string || makeString(name));
        }
        return result;
    };
}
