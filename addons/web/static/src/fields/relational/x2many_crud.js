// @ts-check

/** @module @web/fields/relational/x2many_crud - OWL hook providing CRUD operations (save, update, remove) for x2many fields */

/**
 * Hook providing CRUD operations for x2many fields.
 *
 * @param {Function} getList - Returns the current x2many list
 * @param {boolean} isMany2Many - Whether the field is many2many (vs one2many)
 * @returns {{saveRecord: Function, updateRecord: Function, removeRecord: Function}}
 */
export function useX2ManyCrud(getList, isMany2Many) {
    let saveRecord;
    if (isMany2Many) {
        saveRecord = async (object) => {
            const list = getList();
            if (Array.isArray(object)) {
                return list.addAndRemove({ add: object });
            } else {
                // object instanceof Record
                await object.save({ reload: false });
                return list.linkTo(object.resId);
            }
        };
    } else {
        saveRecord = async (record) => getList().validateExtendedRecord(record);
    }

    const updateRecord = async (record) => {
        if (isMany2Many) {
            await record.save();
        }
        return getList().validateExtendedRecord(record);
    };

    const removeRecord = (record) => {
        const list = getList();
        if (isMany2Many) {
            return list.forget(record);
        }
        return list.delete(record);
    };

    return {
        saveRecord,
        updateRecord,
        removeRecord,
    };
}

/**
 * Hook to add an inline record to an x2many list, with debounce protection.
 *
 * @param {Object} params
 * @param {Function} params.addNew - Function to add a new record to the list
 * @returns {Function} addInlineRecord
 */
export function useAddInlineRecord({ addNew }) {
    let creatingRecord = false;

    async function addInlineRecord({ context, editable }) {
        if (!creatingRecord) {
            creatingRecord = true;
            try {
                await addNew({ context, mode: "edit", position: editable });
            } finally {
                creatingRecord = false;
            }
        }
    }
    return addInlineRecord;
}
