/** odoo-module **/

import { Component, xml } from "@odoo/owl"

export class DefenderHoneypot extends Component {
    //static template = "link_tracker.defender_honeypot"
    static template = xml`<div>hello</div>
    <button t-on-click="activateButt">Butt</button>
    `;
    
    // <p t-on-click="activateP">P element</p>
    // <a href="/arrival-mail-page">YES YES</a>
    activateButt() {
        window.location.href = "/js-button-page"
    }
    activateP() {
        window.location.href = "/href-button-page"

    }
}
