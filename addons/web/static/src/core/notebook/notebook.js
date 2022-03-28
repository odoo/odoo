/** @odoo-module **/

const { Component, useState, onWillUpdateProps } = owl;

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
        this.state = useState({ currentPage: null });
        this.state.currentPage = this.computeActivePage(this.props);

        onWillUpdateProps((nextProps) => this.state.currentPage = this.computeActivePage(nextProps));
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
Notebook.props = ["slots?", "className?"];
