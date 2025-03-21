import { useDomState } from "@html_builder/core/utils";
import { useOperation } from "@html_builder/core/operation_plugin";
import { Component } from "@odoo/owl";

export class NavTabsHeaderMiddleButtons extends Component {
    static template = "html_builder.NavTabsHeaderMiddleButtons";
    static props = {
        addItem: Function,
        removeItem: Function,
    };

    setup() {
        this.state = useDomState((editingElement) => ({
            tabEls: editingElement.querySelectorAll(".s_tabs_nav .nav-item"),
        }));

        this.callOperation = useOperation();
    }

    addItem() {
        this.callOperation(() => {
            this.props.addItem(this.env.getEditingElement());
        });
    }

    removeItem() {
        this.callOperation(() => {
            this.props.removeItem(this.env.getEditingElement());
        });
    }
}
