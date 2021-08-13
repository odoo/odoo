/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";

const { Component } = owl;

export class ControlPanel extends Component {
    setup() {
        this.actionService = useService("action");
    }

    /**
     * @returns {Object}
     */
    get display() {
        const display = Object.assign(
            {
                "top-left": true,
                "top-right": true,
                "bottom-left": true,
                "bottom-right": true,
            },
            this.props.display
        );
        display.top = display["top-left"] || display["top-right"];
        display.bottom = display["bottom-left"] || display["bottom-right"];
        return display;
    }

    /**
     * Called when an element of the breadcrumbs is clicked.
     *
     * @param {string} jsId
     */
    onBreadcrumbClicked(jsId) {
        this.actionService.restore(jsId);
    }

    /**
     * Called when a view is clicked in the view switcher.
     *
     * @param {ViewType} viewType
     */
    onViewClicked(viewType) {
        this.actionService.switchView(viewType);
    }
}

ControlPanel.template = "web.ControlPanel";
ControlPanel.defaultProps = {
    breadcrumbs: [],
    display: {},
};
