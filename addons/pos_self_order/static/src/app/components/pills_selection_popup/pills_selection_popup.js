import { useRef } from "@web/owl2/utils";
import { Component, proxy, props, t } from "@odoo/owl";
import { scrollToSelected } from "@pos_self_order/app/utils/scroll_to_selected";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { getDisplayDateInfo } from "@point_of_sale/utils";

/**
 * PillsSelectionPopup component
 *
 * @props title: string
 * @props subtitle: string
 * @props close: function
 * @props getPayload: function
 * @props options: {
 *   categories: {
 *     [categoryId]: {
 *       id: string,
 *       name: string,
 *       subCategories: {
 *         [subCategoryId]: {
 *           id: string,
 *           name: string,
 *           options: Array<{ id: string, name: string }>
 *         }
 *      }
 *   }
 */
export class PillsSelectionPopup extends Component {
    static template = "pos_self_order.PillsSelectionPopup";
    static components = { Dialog };
    props = props({
        options: t.object(),
        title: t.string(),
        subtitle: t.string(),
        close: t.function(),
        getPayload: t.function(),
        selectionType: t.string(),
    });

    setup() {
        this.ui = useService("ui");
        this.selfOrder = useService("self_order");
        this.categoryListRef = useRef("category-list");
        this.state = proxy({
            selectedCategoryId: this.categories.length > 0 ? this.categories[0].id : null,
            selectedOptionId: null,
        });

        this.onClickScrollTracked = scrollToSelected(
            this.categoryListRef,
            this.selectCategory.bind(this)
        );
    }

    get categories() {
        return Object.values(this.props.options.categories);
    }

    get getSelectedCategorySubCategories() {
        const categoryId = this.state.selectedCategoryId;
        const category = this.props.options.categories[categoryId];
        return category ? Object.values(category.subCategories) : [];
    }

    get getSelectedCategoryOptions() {
        return this.props.options.options[this.state.selectedCategoryId] || [];
    }

    confirmSelection() {
        this.props.getPayload(this.state.selectedOptionId);
        this.props.close();
    }

    selectOption(optionId) {
        this.state.selectedOptionId = optionId;
    }

    selectCategory(categId) {
        this.state.selectedCategoryId = categId;
        this.state.selectedOptionId = null;
    }

    get isTimeSelection() {
        return this.props.selectionType == "time";
    }

    get isTableSelection() {
        return this.props.selectionType == "table";
    }

    getCategoryInfo(category) {
        if (!this.isTimeSelection) {
            return { label: category.name };
        }

        return getDisplayDateInfo(category.id);
    }
}
