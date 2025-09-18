// @ts-check

/** @module @web/fields/relational/special_data - OWL hook for loading and caching special data tied to a record lifecycle */

import { onWillUpdateProps, status, useComponent, useState } from "@odoo/owl";
import { useRecordObserver } from "@web/model/relational_model/record_hooks";
/** @import { Component } from "@odoo/owl" */
/** @import { Services } from "services" */

/**
 * Hook for loading and caching special data (e.g. selection options) tied to a
 * record's lifecycle. Uses ORM disk cache with change detection to keep the
 * data fresh across record navigation.
 *
 * @template T, [Props=any], [Env=any]
 * @param {(orm: Services["orm"], props: Component<Props, Env>["props"]) => Promise<T>} loadFn
 * @returns {{ data: T }}
 */
export function useSpecialData(loadFn) {
    const component = useComponent();
    const record = component.props.record;
    const { specialDataCaches } = record.model;
    const orm = component.env.services.orm;
    const ormWithCache = Object.create(orm);
    ormWithCache.call = async (...args) => {
        const key = JSON.stringify(args);
        if (!specialDataCaches[key]) {
            return await orm
                .cache({
                    type: "disk",
                    update: "always",
                    callback: (res, hasChanged) => {
                        specialDataCaches[key] = Promise.resolve(res);
                        if (status(component) !== "destroyed" && hasChanged) {
                            loadFn(ormWithCache, component.props).then((res) => {
                                result.data = res;
                            });
                        }
                    },
                })
                .call(...args);
        }
        return specialDataCaches[key];
    };

    /** @type {{ data: T }} */
    const result = useState(/** @type {any} */ ({ data: {} }));
    useRecordObserver(async (record, props) => {
        result.data = await loadFn(ormWithCache, { ...props, record });
    });
    onWillUpdateProps(async (props) => {
        // useRecordObserver callback is not called when the record doesn't change
        if (props.record.id === component.props.record.id) {
            result.data = await loadFn(ormWithCache, props);
        }
    });
    return result;
}
