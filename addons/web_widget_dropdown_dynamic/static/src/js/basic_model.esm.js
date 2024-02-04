/** @odoo-module **/
import BasicModel from "web.BasicModel";

BasicModel.include({
    /**
     * Fetches all the values associated to the given fieldName.
     *
     * @param {Object} record - an element from the localData
     * @param {Object} fieldName - the name of the field
     * @param {Object} fieldInfo
     * @returns {Promise<any>}
     *          The promise is resolved with the fetched special values.
     *          If this data is the same as the previously fetched one
     *          (for the given parameters), no RPC is done and the promise
     *          is resolved with the undefined value.
     */
    _fetchDynamicDropdownValues: function (record, fieldName, fieldInfo) {
        var model = fieldInfo.options.model || record.model;
        var method = fieldInfo.values || fieldInfo.options.values;
        if (!method) {
            return Promise.resolve();
        }

        var context = record.getContext({fieldName: fieldName});

        // Avoid rpc if not necessary
        var hasChanged = this._saveSpecialDataCache(record, fieldName, {
            context: context,
        });
        if (!hasChanged) {
            return Promise.resolve();
        }

        return this._rpc({
            model: model,
            method: method,
            context: context,
        }).then(function (result) {
            var new_result = result.map((val_updated) => {
                return val_updated.map((e) => {
                    if (typeof e !== "string") {
                        return String(e);
                    }
                    return e;
                });
            });
            return new_result;
        });
    },
});
