/**
 * OD19 Web Navigation — systray buttons (Back / Forward)
 */

import { Component, xml } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class Od19NavButtons extends Component {
    static template = xml`
        <div class="od19-nav-glass" role="group" aria-label="ประวัติการนำทาง">
            <button type="button" class="od19-nav-glass__btn"
                title="ย้อนกลับ (Alt + ←)"
                aria-label="ย้อนกลับ"
                t-on-click="() => this.nav.back()">
                <i class="fa fa-chevron-left" aria-hidden="true"/>
            </button>
            <button type="button" class="od19-nav-glass__btn"
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

registry.category("systray").add(
    "od19_web_navigation.nav_buttons",
    { Component: Od19NavButtons },
    { sequence: 20 }
);
