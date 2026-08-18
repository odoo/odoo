import { Component, useProps, t } from "@odoo/owl";
import { useDomState } from "@html_builder/core/utils";
import { useOperation } from "@html_builder/core/operation_plugin";

export class ReferencesCarouselHeaderMiddleButtons extends Component {
    static template = "website.ReferencesCarouselHeaderMiddleButtons";
    props = useProps({
        addItem: t.function(),
        removeItem: t.function(),
    });

    setup() {
        this.callOperation = useOperation();
        this.state = useDomState((editingElement) => {
            const itemEls = editingElement.parentElement.querySelectorAll(
                ":scope > .s_references_carousel_item"
            );
            return {
                disableRemoveButton: itemEls.length <= 1,
            };
        });
    }

    addItem() {
        this.callOperation(() => {
            this.props.addItem(this.env.getEditingElement());
        });
    }

    removeItem() {
        if (!this.state.disableRemoveButton) {
            this.callOperation(() => {
                this.props.removeItem(this.env.getEditingElement());
            });
        }
    }
}
