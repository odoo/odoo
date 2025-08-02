import { Component, useState } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { toolbarButtonProps } from "@html_editor/main/toolbar/toolbar";
import { useDropdownAutoVisibility } from "@html_editor/dropdown_autovisibility_hook";
import { useChildRef } from "@web/core/utils/hooks";

export class AlignSelector extends Component {
    static template = "html_editor.AlignSelector";
    static props = {
        getItems: Function,
        getDisplay: Function,
        onSelected: Function,
        ...toolbarButtonProps,
    };
    static components = { Dropdown, DropdownItem };

    setup() {
<<<<<<< 9df334c0aca8a57dcbed4c87b43b18403f3a7c6e:addons/html_editor/static/src/main/align/align_selector.js
        this.items = this.props.getItems();
        this.state = useState(this.props.getDisplay());
||||||| b8c55ff9da25ccfc84d0e588aa790d0080cc8a55:addons/html_editor/static/src/main/media/image_padding.js
        this.paddings = { None: 0, Small: 1, Medium: 2, Large: 3, XL: 5 };
=======
        this.paddings = { None: 0, Small: 1, Medium: 2, Large: 3, XL: 5 };
        this.menuRef = useChildRef();
        useDropdownAutoVisibility(this.env.overlayState, this.menuRef);
>>>>>>> 2bdeb18cf3cc3744a382fb402229e58ac9dd0059:addons/html_editor/static/src/main/media/image_padding.js
    }

    onSelected(item) {
        this.props.onSelected(item);
    }
}
