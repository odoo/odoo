/** @odoo-module **/

import { Popover } from "./popover";

const { Component } = owl;
const { useExternalListener, useState } = owl.hooks;
const { xml } = owl.tags;

class PopoverController extends Component {
    setup() {
        this.state = useState({ displayed: false });
        this.targetObserver = new MutationObserver(this.onTargetMutate.bind(this));

        useExternalListener(window, "click", this.onClickAway, { capture: true });
    }
    mounted() {
        this.targetObserver.observe(this.target.parentElement, { childList: true });
    }
    willUnmount() {
        this.targetObserver.disconnect();
    }

    shouldUpdate() {
        return false;
    }

    get popoverProps() {
        return {
            target: this.target,
            position: this.props.position,
            popoverClass: this.props.popoverClass,
        };
    }
    get target() {
        if (typeof this.props.target === "string") {
            return document.querySelector(this.props.target);
        } else {
            return this.props.target;
        }
    }
    onClickAway(ev) {
        if (this.target.contains(ev.target) || ev.target.closest(".o_popover")) {
            return;
        }
        if (this.props.closeOnClickAway) {
            this.props.close();
        }
    }
    onTargetMutate() {
        const target = this.target;
        if (!target || !target.parentElement) {
            this.props.close();
        }
    }
}
PopoverController.components = { Popover };
PopoverController.defaultProps = {
    alwaysDisplayed: false,
    closeOnClickAway: true,
};
PopoverController.template = xml/*xml*/ `
    <Popover t-props="popoverProps" t-on-popover-closed="props.close()">
        <t t-component="props.Component" t-props="props.props" />
    </Popover>
`;

export class PopoverContainer extends Component {
    setup() {
        this.props.bus.on("UPDATE", this, this.render);
    }
}
PopoverContainer.components = { PopoverController };
PopoverContainer.template = xml`
    <div class="o_popover_container">
        <t t-foreach="Object.values(props.popovers)" t-as="popover" t-key="popover.id">
            <PopoverController t-props="popover" />
        </t>
    </div>
`;
