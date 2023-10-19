/* @odoo-module */

import { Component, xml } from "@odoo/owl";
import { MainComponentsContainer } from "@web/core/main_components_container";

// This component wraps the main components container to add a position fixed
// to the bottom of the screen. This prevents the emoji picker from scrolling
// up the page when it is opened.
export class LivechatContainer extends Component {
    static components = { MainComponentsContainer };
    static template = xml`
        <div class="position-fixed">
            <MainComponentsContainer/>
        </div>
    `;
}
