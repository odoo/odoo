import { CommandResult } from "../../o_spreadsheet/cancelled_reason";
import { checkFilterFieldMatching } from "@spreadsheet/global_filters/helpers";
import { deepCopy } from "@web/core/utils/objects";
import { OdooCorePlugin } from "@spreadsheet/plugins";

/**
 * @typedef GFLocalList
 * @property {string} id
 * @property {Record<string, FieldMatching>} fieldMatching
 *
 */

export class ListCoreGlobalFilterPlugin extends OdooCorePlugin {
    static getters = /** @type {const} */ (["getListFieldMatch", "getListFieldMatching"]);
    constructor(config) {
        super(config);

        /** @type {Object.<string, GFLocalList>} */
        this.fieldMatchings = {};
    }

    /**
     * @param {AllCoreCommand} cmd
     *
     * @returns {string | string[]}
     */
    allowDispatch(cmd) {
        switch (cmd.type) {
            case "ADD_GLOBAL_FILTER":
            case "EDIT_GLOBAL_FILTER":
                if (cmd.list) {
                    return checkFilterFieldMatching(cmd.list);
                }
        }
        return CommandResult.Success;
    }

    /**
     * @param {AllCoreCommand} cmd
     *
     */
    handle(cmd) {
        switch (cmd.type) {
            case "INSERT_ODOO_LIST": {
                this._addList(cmd.id);
                break;
            }
            case "REMOVE_ODOO_LIST": {
                this.history.update("fieldMatchings", cmd.listId, undefined);
                break;
            }
            case "DUPLICATE_ODOO_LIST": {
                const { listId, newListId } = cmd;
                const fieldMatch = deepCopy(this.fieldMatchings[listId]);
                this._addList(newListId, fieldMatch);
                break;
            }
            case "ADD_GLOBAL_FILTER":
            case "EDIT_GLOBAL_FILTER":
                if (cmd.list) {
                    this._setListFieldMatching(cmd.filter.id, cmd.list);
                }
                break;
            case "REMOVE_GLOBAL_FILTER":
                this._onFilterDeletion(cmd.id);
                break;
        }
    }

    // -------------------------------------------------------------------------
    // Getters
    // -------------------------------------------------------------------------

    /**
     * @param {string} id
     * @returns {string}
     */
    getListFieldMatch(id) {
        return this.fieldMatchings[id];
    }

    /**
     *
     * @param {string} listId
     * @param {string} filterId
     */
    getListFieldMatching(listId, filterId) {
        return this.getListFieldMatch(listId)[filterId];
    }

    // -------------------------------------------------------------------------
    // Private
    // -------------------------------------------------------------------------

    /**
     * Sets the current FieldMatching on a list
     *
     * @param {string} filterId
     * @param {Record<string,FieldMatching>} listFieldMatches
     */
    _setListFieldMatching(filterId, listFieldMatches) {
        const fieldMatchings = { ...this.fieldMatchings };
        for (const [listId, fieldMatch] of Object.entries(listFieldMatches)) {
            fieldMatchings[listId][filterId] = fieldMatch;
        }
        this.history.update("fieldMatchings", fieldMatchings);
    }

    _onFilterDeletion(filterId) {
        const fieldMatchings = { ...this.fieldMatchings };
        for (const listId in fieldMatchings) {
            this.history.update("fieldMatchings", listId, filterId, undefined);
        }
    }

    _addList(id, fieldMatching = undefined) {
        const list = this.getters.getListDefinition(id);
        const model = list.model;
        this.history.update(
            "fieldMatchings",
            id,
            fieldMatching || this.getters.getFieldMatchingForModel(model)
        );
    }

    // ---------------------------------------------------------------------
    // Import/Export
    // ---------------------------------------------------------------------

    /**
     * @param {Object} data
     */
    import(data) {
        if (data.lists) {
            for (const [id, list] of Object.entries(data.lists)) {
                this._addList(id, list.fieldMatching ?? {});
            }
        }
    }
    /**
     *
     * @param {Object} data
     */
    export(data) {
        for (const id in this.fieldMatchings) {
            data.lists[id].fieldMatching = this.fieldMatchings[id];
        }
    }
}
