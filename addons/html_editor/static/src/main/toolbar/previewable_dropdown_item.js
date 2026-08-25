import { Component, t, useProps } from "@odoo/owl";
import { DropdownItem, dropdownItemProps } from "@web/core/dropdown/dropdown_item";

export class PreviewableDropdownItem extends Component {
    static template = "html_editor.PreviewableDropdownItem";
    static components = { DropdownItem };
    props = useProps({
        ...dropdownItemProps,
        item: t.any(),
        preview: t.object(),
    });

    get dropdownProps() {
        const props = { ...this.props };
        delete props.item;
        delete props.preview;
        return props;
    }
}
