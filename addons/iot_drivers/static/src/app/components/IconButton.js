/* global owl */

import useStore from "../hooks/useStore.js";

const { Component, xml } = owl;

export class IconButton extends Component {
    static props = {
        onClick: Function,
        icon: String,
    };

    setup() {
        this.store = useStore();
    }

    static template = xml`
    <div class="d-flex align-items-center justify-content-center icon-button btn btn-primary" t-translation="off" t-on-click="this.props.onClick">
        <i class="fa" t-att-class="this.props.icon" aria-hidden="true"></i>
    </div>
  `;
}
