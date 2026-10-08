import { _t } from "@web/core/l10n/translation";
import { Component, useProps, proxy, t } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

export class SelectionPopup extends Component {
    static template = "point_of_sale.SelectionPopup";
    static components = { Dialog };
    props = useProps({
        title: t.string().optional(_t("Select")),
        list: t.array().optional([]),
        getPayload: t.function(),
        close: t.function(),
        size: t.string().optional("lg"),
        bodyClass: t.string().optional(""),
        stars: t.boolean().optional(false),
        onStarClick: t.function().optional(),
    });

    /**
     * Value of the `item` key of the selected element in the Selection
     * Array is the payload of this popup.
     *
     * @param {Object} props
     * @param {String} [props.title='Select']
     * @param {Array<Selection>} [props.list=[]]
     *      Selection {
     *          id: integer,
     *          label: string,
     *          isSelected: boolean,
     *          item: any,
     *      }
     */
    setup() {
        this.state = proxy({
            selectedId: this.props.list.find((item) => item.isSelected),
            list: this.props.list,
        });
    }
    selectItem(itemId) {
        this.state.selectedId = itemId;
        this.confirm();
    }
    computePayload() {
        const selected = this.props.list.find((item) => this.state.selectedId === item.id);
        return selected && selected.item;
    }
    confirm() {
        this.props.getPayload(this.computePayload());
        this.props.close();
    }
    async star(itemId) {
        if (!this.props.onStarClick) {
            return;
        }

        await this.props.onStarClick(itemId);

        for (const item of this.state.list) {
            item.isStarred = item.id === itemId;
        }
    }
}
