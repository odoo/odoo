import { useDraggable } from "./draggable_hook";
import { Sortable } from "./sortable";

/**
 * @typedef {import("./sortable").SortableParameters} SortableParameters
 */

/**
 * @template {typeof Sortable} [T=Sortable]
 * @param {T | SortableParameters} ClassOrParams
 * @param {SortableParameters} [params]
 * @returns {InstanceType<T>}
 */
export function useSortable(ClassOrParams, params) {
    if (typeof ClassOrParams !== "function") {
        params = ClassOrParams;
        ClassOrParams = Sortable;
    }
    return useDraggable(ClassOrParams, params);
}
