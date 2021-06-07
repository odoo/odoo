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
    get popoverProps() {
        return {
            ...this.props.popoverProps,
            target: this.target,
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
            this.trigger("popover-closed");
        }
    }
    onTargetMutate() {
        const target = this.target;
        if (!target || !target.parentElement) {
            this.trigger("popover-closed");
        }
    }
}
PopoverController.components = { Popover };
PopoverController.defaultProps = {
    alwaysDisplayed: false,
    closeOnClickAway: true,
};
PopoverController.template = xml/*xml*/ `
    <Popover t-props="popoverProps" t-on-close="onClose">
        <t t-component="props.Component" t-props="props.componentProps" />
    </Popover>
`;

export class PopoverContainer extends Component {
    setup() {
        // do not include popover params in state to keep original popover props
        this.popovers = {};
        this.props.bus.on("ADD", this, this.add);
        this.props.bus.on("REMOVE", this, this.remove);
    }
    __destroy() {
        this.props.bus.off("ADD", this, this.add);
        this.props.bus.off("REMOVE", this, this.remove);
        super.__destroy();
    }

    /**
     * @param {Object}      params
     * @param {number}      params.id
     * @param {any}         params.Component
     * @param {Object}      params.props
     * @param {() => void}  params.onClose
     * @param {string}      params.position
     * @param {string}      params.popoverClass
     * @param {string}      params.target
     * @param {boolean}     params.closeOnClickAway
     */
    add(params) {
        this.popovers[params.id] = {
            id: params.id,
            onClose: params.onClose,
            controllerProps: {
                target: params.target,
                closeOnClickAway: params.closeOnClickAway,
                Component: params.Component,
                componentProps: params.props,
                popoverProps: {
                    position: params.position,
                    popoverClass: params.popoverClass,
                },
            },
        };

        this.render();
    }
    /**
     * @param {number} id
     */
    remove(id) {
        delete this.popovers[id];
        this.render();
    }

    /**
     * @param {number} id
     */
    onPopoverClosed(id) {
        if (!(id in this.popovers)) {
            // It can happen that the popover was removed manually just before this call
            return;
        }
        const popover = this.popovers[id];
        if (popover.onClose) {
            popover.onClose();
        }
        this.remove(id);
    }
}
PopoverContainer.components = { PopoverController };
PopoverContainer.template = xml`
    <div class="o_popover_container">
        <t t-foreach="Object.values(popovers)" t-as="popover" t-key="popover.id">
            <PopoverController
                t-props="popover.controllerProps"
                t-on-popover-closed="onPopoverClosed(popover.id)"
            />
        </t>
    </div>
`;
