/** @odoo-module **/

import { Domain } from "@web/core/domain";
import { useService } from "@web/core/utils/hooks";
import { TagsList } from "@web/views/fields/many2many_tags/tags_list";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";

const { Component, onWillStart, onWillUpdateProps } = owl;

export class RecordsSelector extends Component {
    setup() {
        /** @type {Record<number, string>} */
        this.displayNames = {};
        /** @type {import("@web/core/orm_service").ORM}*/
        this.orm = useService("orm");
        onWillStart(() => this.fetchMissingDisplayNames(this.props.resModel, this.props.resIds));
        onWillUpdateProps((nextProps) =>
            this.fetchMissingDisplayNames(nextProps.resModel, nextProps.resIds)
        );
    }

    get tags() {
        return this.props.resIds.map((id) => ({
            text: this.displayNames[id],
            onDelete: () => this.removeRecord(id),
            displayBadge: true,
        }));
    }

    searchDomain() {
        return Domain.not([["id", "in", this.props.resIds]]).toList();
    }

    /**
     * @param {number} recordId
     */
    removeRecord(recordId) {
        delete this.displayNames[recordId];
        this.notifyChange(this.props.resIds.filter((id) => id !== recordId));
    }

    /**
     * @param {{ id: number; name?: string}[]} records
     */
    update(records) {
        for (const record of records.filter((record) => record.name)) {
            this.displayNames[record.id] = record.name;
        }
        this.notifyChange(this.props.resIds.concat(records.map(({ id }) => id)));
    }

    /**
     * @param {number[]} selectedIds
     */
    notifyChange(selectedIds) {
        this.props.onValueChanged(
            selectedIds.map((id) => ({ id, display_name: this.displayNames[id] }))
        );
    }

    /**
     * @param {string} resModel
     * @param {number[]} recordIds
     */
    async fetchMissingDisplayNames(resModel, recordIds) {
        const missingNameIds = recordIds.filter((id) => !(id in this.displayNames));
        if (missingNameIds.length === 0) {
            return;
        }
        const results = await this.orm.read(resModel, missingNameIds, ["display_name"]);
        for (const { id, display_name } of results) {
            this.displayNames[id] = display_name;
        }
    }
}
RecordsSelector.components = { TagsList, Many2XAutocomplete };
RecordsSelector.template = "spreadsheet.RecordsSelector";
RecordsSelector.props = {
    /**
     * Callback called when a record is selected or removed.
     * (selectedRecords: Array<{ id: number; display_name: string }>) => void
     **/
    onValueChanged: Function,
    resModel: String,
    /**
     * Array of selected record ids
     */
    resIds: {
        optional: true,
        type: Array,
    },
    placeholder: {
        optional: true,
        type: String,
    },
};
RecordsSelector.defaultProps = {
    resIds: [],
};
