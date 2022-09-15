/** @odoo-module **/

import { Domain } from "@web/core/domain";
import { useService } from "@web/core/utils/hooks";
import { TagsList } from "@web/views/fields/many2many_tags/tags_list";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";

const { Component, xml, onWillStart, onWillUpdateProps } = owl;

export class X2ManyTagSelector extends Component {
    setup() {
        /** @type {Record<number, string>} */
        this.displayNames = {};
        /** @type {import("@web/core/orm_service").ORM}*/
        this.orm = useService("orm");
        onWillStart(() =>
            this.fetchMissingDisplayNames(this.props.relatedModel, this.props.selectedValues)
        );
        onWillUpdateProps((nextProps) =>
            this.fetchMissingDisplayNames(nextProps.relatedModel, nextProps.selectedValues)
        );
    }

    get tags() {
        return this.props.selectedValues.map((id) => ({
            text: this.displayNames[id],
            onDelete: () => this.removeRecord(id),
            displayBadge: true,
        }));
    }

    searchDomain() {
        return Domain.not([["id", "in", this.props.selectedValues]]).toList();
    }

    /**
     * @param {number} recordId
     */
    removeRecord(recordId) {
        delete this.displayNames[recordId];
        this.notifyChange(this.props.selectedValues.filter((id) => id !== recordId));
    }

    /**
     * @param {{ id: number; name?: string}[]} records
     */
    update(records) {
        for (const record of records.filter((record) => record.name)) {
            this.displayNames[record.id] = record.name;
        }
        this.notifyChange(this.props.selectedValues.concat(records.map(({ id }) => id)));
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
X2ManyTagSelector.components = { TagsList, Many2XAutocomplete };
X2ManyTagSelector.template = xml/*xml*/ `
    <div class="o_field_widget o_field_many2many_tags">
        <div class="o_field_tags d-inline-flex flex-wrap mw-100 o_tags_input o_input">
            <TagsList tags="tags"/>
            <div class="o_field_many2many_selection d-inline-flex w-100">
                <Many2XAutocomplete
                    placeholder="props.placeholder"
                    resModel="props.relatedModel"
                    fieldString="props.placeholder"
                    activeActions="{}"
                    update.bind="update"
                    getDomain.bind="searchDomain"
                    isToMany="true"
                />
            </div>
        </div>
    </div>`;
X2ManyTagSelector.props = {
    /**
     * Callback called when a record is selected or removed.
     * (selectedRecords: Array<{ id: number; display_name: string }>) => void
     **/
    onValueChanged: Function,
    relatedModel: String,
    /**
     * Array of selected record ids
     */
    selectedValues: {
        optional: true,
        type: Array,
    },
    placeholder: {
        optional: true,
        type: String,
    },
};
X2ManyTagSelector.defaultProps = {
    selectedValues: [],
};
