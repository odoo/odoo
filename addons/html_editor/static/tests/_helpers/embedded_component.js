import { useEditableDescendants } from "@html_editor/others/embedded_component_utils";
import { Component, useRef, useState, xml } from "@odoo/owl";

export class Counter extends Component {
    static props = ["*"];
    static template = xml`
        <span t-ref="root" class="counter" t-on-click="increment">Counter:<t t-esc="state.value"/></span>`;

    state = useState({ value: 0 });
    ref = useRef("root");

    increment() {
        this.state.value++;
    }
}

export const EmbeddedWrapperMixin = (editableDescendantName) =>
    class extends Component {
        static props = ["*"];
        static template = xml`<t><div class="${editableDescendantName}" t-ref="${editableDescendantName}"/></t>`;

        setup() {
            useEditableDescendants(this.props.host);
        }
    };

export class EmbeddedWrapper extends Component {
    static props = ["*"];
    static template = xml`
        <t>
            <div t-if="editableDescendants.shallow" class="shallow" t-ref="shallow"/>
            <div t-if="!state.switch">
                <div class="deep" t-ref="deep"/>
            </div>
            <div t-else="">
                <div class="switched">
                    <div class="deep" t-ref="deep"/>
                </div>
            </div>
        </t>`;

    setup() {
        this.editableDescendants = useEditableDescendants(this.props.host);
        this.state = useState({
            switch: false,
        });
    }
}

export function embedding(name, Component, getProps, getEditableDescendants) {
    return {
        name,
        Component,
        getProps,
        getEditableDescendants,
    };
}
