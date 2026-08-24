import { onWillUnmount, reactive, useEffect } from "@odoo/owl";
import { Draggable } from "./draggable";

/**
 *
 * @typedef {import("./draggable").DraggableParameters} DraggableParameters
 */

/**
 * @template {typeof Draggable} [T=Draggable]
 * @param {T | DraggableParameters} ClassOrParams
 * @param {DraggableParameters} [params]
 * @returns {InstanceType<T>}
 */
export function useDraggable(ClassOrParams, params) {
    if (typeof ClassOrParams !== "function") {
        params = ClassOrParams;
        ClassOrParams = Draggable;
    }
    return new ClassOrParams(params, {
        update: useEffect,
        destroy: onWillUnmount,
        wrapState: reactive,
    });
}
