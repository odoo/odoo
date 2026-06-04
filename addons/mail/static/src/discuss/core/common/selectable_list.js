import { DiscussAvatar } from "@mail/core/common/discuss_avatar";

import { Component, props, signal, t } from "@odoo/owl";

import { useAutofocus } from "@web/core/utils/hooks";

const DEFAULT_ITEM_TEMPLATE = "discuss.SelectableList-item";

export class DiscussSelectableList extends Component {
    static components = { DiscussAvatar };
    static template = "discuss.SelectableList";

    inputRef = signal(null);

    setup() {
        super.setup();
        this.props = props({
            items: t.array(t.record()),
            itemTemplate: t.string().optional(DEFAULT_ITEM_TEMPLATE),
            maxSelections: t.number().optional(),
            onToggle: t.function(),
            search: t
                .object({
                    inputId: t.string().optional(),
                    onInput: t.function(),
                    placeholder: t.string().optional(),
                    value: t.string(),
                })
                .optional(),
            selected: t.array(t.record()),
            slots: t
                .object({
                    preface: t.object().optional(),
                    search: t.object().optional(),
                    searchStatus: t.object().optional(),
                    searchTrailing: t.object().optional(),
                    listHint: t.object().optional(),
                    empty: t.object().optional(),
                    selected: t.object().optional(),
                    footer: t.object().optional(),
                })
                .optional(),
        });
        if (this.props.search) {
            useAutofocus({ ref: this.inputRef });
        }
    }

    get itemTemplate() {
        return this.props.itemTemplate ?? DEFAULT_ITEM_TEMPLATE;
    }

    get searchInputId() {
        return this.props.search?.inputId ?? "o-discuss-SelectableList-search";
    }

    isSelected(item) {
        return this.props.selected.some((selected) => selected.key === item.key);
    }

    onInput() {
        this.props.search?.onInput(this.inputRef()?.value ?? "");
    }

    onClickItem(item) {
        if (
            !this.isSelected(item) &&
            this.props.maxSelections &&
            this.props.selected.length >= this.props.maxSelections
        ) {
            return;
        }
        this.props.onToggle(item);
    }
}
