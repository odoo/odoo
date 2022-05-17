/** @odoo-module **/

import { scrollTo } from "@web/core/utils/scrolling";

const { Component, useEffect, useRef, useState, onWillUpdateProps } = owl;

/**
 * A notebook component that will render only the current page and allow
 * switching between its pages.
 *
 * <Notebook
 *    <t t-set-slot="Page Name 1" title="Some Title" isVisible="bool">
 *      <div>Page Content 1</div>
 *    </t>
 *    <t t-set-slot="Page Name 2" title="Some Title" isVisible="bool">
 *      <div>Page Content 2</div>
 *    </t>
 * </Notebook>
 *
 * @extends Component
 */

export class Notebook extends Component {
    setup() {
        this.activePane = useRef("activePane");
        this.anchorTarget = null;
        this.state = useState({ currentPage: null });
        this.state.currentPage = this.computeActivePage(this.props);
        this.env.bus.addEventListener("SCROLLER:ANCHOR_LINK_CLICKED", (ev) =>
            this.onAnchorClicked(ev)
        );
        useEffect(
            () => {
                if (this.anchorTarget) {
                    const matchingEl = this.activePane.el.querySelector(`#${this.anchorTarget}`);
                    scrollTo(matchingEl, { isAnchor: true });
                    this.anchorTarget = null;
                }
            },
            () => [this.state.currentPage]
        );
        onWillUpdateProps(
            (nextProps) => (this.state.currentPage = this.computeActivePage(nextProps))
        );
    }

    onAnchorClicked(ev) {
        if (!this.props.anchors) return;
        const id = ev.detail.detail.id.substring(1);
        if (this.props.anchors[id]) {
            if (this.state.currentPage !== this.props.anchors[id].target) {
                ev.preventDefault();
                ev.detail.detail.originalEv.preventDefault();
                this.anchorTarget = id;
                this.state.currentPage = this.props.anchors[id].target;
            }
        }
    }

    computeActivePage(props) {
        if (!props.slots) {
            return null;
        }
        const current = this.state.currentPage;
        const pages = props.slots;
        if (!current || (current && !pages[current].isVisible)) {
            const candidate = Object.entries(props.slots).find(([k, v]) => v.isVisible);
            return candidate ? candidate[0] : null;
        }
        return current;
    }
}

Notebook.template = "web.Notebook";
Notebook.props = ["slots?", "class?", "className?", "anchors?"];
