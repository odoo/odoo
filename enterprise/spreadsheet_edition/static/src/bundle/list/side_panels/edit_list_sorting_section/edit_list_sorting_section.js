import { Component, useRef } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { CheckBox } from "@web/core/checkbox/checkbox";
import { useSortable } from "@web/core/utils/sortable_owl";
import { components } from "@odoo/o-spreadsheet";
const { AddDimensionButton, Section } = components;

export class EditListSortingSection extends Component {
    static template = "spreadsheet_edition.EditListSortingSection";
    static components = { Dialog, CheckBox, AddDimensionButton, Section };
    static props = {
        onUpdateSorting: Function,
        orderBy: Array,
        fields: Object,
        resModel: String,
    };

    setup() {
        this.mainRef = useRef("main");
        useSortable({
            enable: true,
            ref: this.mainRef,
            elements: ".o_draggable",
            cursor: "move",
            delay: 100,
            tolerance: 10,
            ignore: "select",
            onDrop: (params) => this._onSortDrop(params),
        });
    }

    /**
     * @param {Object} params
     * @param {HTMLElement} params.element
     * @param {HTMLElement} params.previous
     */
    _onSortDrop({ element, previous }) {
        const orderByArray = [...this.props.orderBy];
        const elementIndex = orderByArray.findIndex((order) => order.name === element.dataset.id);
        const orderBy = orderByArray[elementIndex];
        orderByArray.splice(elementIndex, 1);
        const newIndex = previous
            ? orderByArray.findIndex((order) => order.name === previous.dataset.id) + 1
            : 0;
        orderByArray.splice(newIndex, 0, orderBy);
        this.updateSorting(orderByArray);
    }

    updateSorting(orderBy) {
        this.props.onUpdateSorting(orderBy);
    }

    isFieldAllowed(field) {
        return field.sortable && !this.props.orderBy.map((el) => el.name).includes(field.name);
    }

    getAllowedFields() {
        return Object.values(this.props.fields)
            .filter((field) => this.isFieldAllowed(field))
            .sort((a, b) => a.string.localeCompare(b.string));
    }

    onAddSortingRule(fieldName) {
        const orderByArray = [...this.props.orderBy, { name: fieldName, asc: true }];
        this.updateSorting(orderByArray);
    }

    onDeleteSortingRule(ruleIndex) {
        const orderByArray = [...this.props.orderBy];
        orderByArray.splice(ruleIndex, 1);
        this.updateSorting(orderByArray);
    }

    toggleAscending(ruleIndex) {
        const orderByArray = [...this.props.orderBy];
        orderByArray[ruleIndex] = {
            ...orderByArray[ruleIndex],
            asc: !orderByArray[ruleIndex].asc,
        };
        this.updateSorting(orderByArray);
    }
}
