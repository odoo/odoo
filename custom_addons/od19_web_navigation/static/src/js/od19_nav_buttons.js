/**
 * OD19 Web Navigation — Back / Forward buttons placed before the Home Menu.
 */

import { Component, xml } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { NavBar } from "@web/webclient/navbar/navbar";

export class Od19NavButtons extends Component {
    static template = xml`
        <div class="od19-nav-segmented" role="group" aria-label="ประวัติการนำทาง">
            <button type="button" class="od19-nav-segmented__btn"
                title="ย้อนกลับ (Alt + ←)"
                aria-label="ย้อนกลับ"
                t-on-click="() => this.nav.back()">
                <i class="fa fa-chevron-left" aria-hidden="true"/>
            </button>
            <span class="od19-nav-segmented__divider" aria-hidden="true"/>
            <button type="button" class="od19-nav-segmented__btn"
                t-att-disabled="!this.canGoForward"
                title="ไปข้างหน้า (Alt + →)"
                aria-label="ไปข้างหน้า"
                t-on-click="() => this.nav.forward()">
                <i class="fa fa-chevron-right" aria-hidden="true"/>
            </button>
        </div>
    `;
    static props = {};

    setup() {
        this.nav = useService("od19_nav_history");
    }

    get canGoForward() {
        const { cursor, entries } = this.nav.state;
        return cursor < entries.length - 1;
    }
}

// The buttons are injected right before the Home Menu through a `web.NavBar`
// template extension (see static/src/xml/od19_nav_buttons.xml), so the NavBar
// component must be aware of Od19NavButtons to be able to render it.
patch(NavBar, {
    components: {
        ...NavBar.components,
        Od19NavButtons,
    },
});
