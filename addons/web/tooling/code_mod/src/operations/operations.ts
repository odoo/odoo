import { remove_odoo_module_comment } from "../operations/remove_odoo_module_comment";
import { view_object_to_controller } from "../operations/view_object_to_controller";
import { Env } from "../utils/env";
import { group_imports, remove_unused_imports } from "../utils/imports";

const OPERATIONS: Record<string, (env: Env) => void> = {
    view_object_to_controller,
    remove_odoo_module_comment,
    group_imports,
    remove_unused_imports,
};

export function processOperationArg(operation: string) {
    const operations: ((env: Env) => void)[] = [];
    for (const op of operation.split(",")) {
        if (!OPERATIONS[op]) {
            throw new Error(`Operation: ${op} not known`);
        }
        operations.push(OPERATIONS[op]);
    }
    return operations;
}
