import { Component, xml, useRef, onMounted, useState } from "@odoo/owl";

class Card extends Component {
    static template = xml`
        <div class="card m-1" style="width: 25rem;">
          <div class="card-body">
            <h5 class="card-title"><t t-esc="props.title"/><span class="badge text-bg-secondary cursor-pointer" t-on-click="toggle">toggle</span></h5>
            <div t-ref="content" contenteditable="true" data-oe-protected="false" t-if="state.isOpen">
            </div>
          </div>
        </div>`;
    static props = { title: String, content: String };

    setup() {
        this.contentRef = useRef("content");
        this.state = useState({ isOpen: true });
        onMounted(() => {
            this.contentRef.el.innerHTML = this.props.content;
        });
    }

    toggle() {
        this.state.isOpen = !this.state.isOpen;
    }
}

export const card = {
    name: "card",
    Component: Card,
    getProps: (elem) => {
        return {
            title: elem.dataset.title || "Some Card",
            content: elem.innerHTML,
        };
    },
};
