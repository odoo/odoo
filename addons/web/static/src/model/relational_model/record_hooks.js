// @ts-check

/** @module @web/model/relational_model/record_hooks - OWL hooks for observing record value changes in field components */

import { onWillDestroy, onWillStart, onWillUpdateProps, useComponent } from "@odoo/owl";
/**
 * This hook should only be used in a component field because it
 * depends on the record props.
 * The callback will be executed once during setup and each time
 * a record value read in the callback changes.
 * @param {(record: any, props?: any) => void | Promise<void>} callback
 */
import { Deferred } from "@web/core/utils/concurrency";
import { uniqueId } from "@web/core/utils/functions";
import { effect } from "@web/core/utils/reactive";
import { batched } from "@web/core/utils/timing";
export function useRecordObserver(callback) {
    const component = useComponent();
    let currentId;
    const observeRecord = (props) => {
        currentId = uniqueId();
        if (!props.record) {
            return;
        }
        const def = new Deferred();
        const effectId = currentId;
        let firstCall = true;
        effect(
            (record) => {
                if (firstCall) {
                    firstCall = false;
                    return Promise.resolve(callback(record, props))
                        .then(def.resolve)
                        .catch(def.reject);
                } else {
                    return batched(
                        (record) => {
                            if (effectId !== currentId) {
                                // effect doesn't clean up when the component is unmounted.
                                // We must do it manually.
                                return;
                            }
                            return Promise.resolve(callback(record, props))
                                .then(def.resolve)
                                .catch(def.reject);
                        },
                        () =>
                            new Promise((resolve) =>
                                window.requestAnimationFrame(() => resolve()),
                            ),
                    )(record);
                }
            },
            [props.record],
        );
        return def;
    };
    onWillDestroy(() => {
        currentId = uniqueId();
    });
    onWillStart(() => observeRecord(component.props));
    onWillUpdateProps((nextProps) => {
        if (nextProps.record !== component.props.record) {
            return observeRecord(nextProps);
        }
    });
}
