/** Auto-Info Employee Shortcut Menu — one-click employee links in the systray. */
import { Component, xml } from "@odoo/owl";

import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class ShortcutMenu extends Component {
    static template = xml`
        <Dropdown position="'bottom-end'" bottomSheet="false">
            <button title="เมนูลัดพนักงาน">
                <i class="fa fa-lg fa-bolt"/>
            </button>
            <t t-set-slot="content">
                <DropdownItem onSelected="() => this.openPortal()">
                    <i class="fa fa-user-circle me-2"/>Employee Portal
                </DropdownItem>
                <DropdownItem onSelected="() => this.openAction('od19_meeting_room_booking.action_meeting_room_booking')">
                    <i class="fa fa-calendar-check-o me-2"/>จองห้องประชุม
                </DropdownItem>
                <DropdownItem onSelected="() => this.openAction('od19_announcement.announcement_action')">
                    <i class="fa fa-bullhorn me-2"/>ประกาศ
                </DropdownItem>
                <DropdownItem onSelected="() => this.openAction('web_tour.tour_action')">
                    <i class="fa fa-book me-2"/>คู่มือการใช้งาน
                </DropdownItem>
            </t>
        </Dropdown>
    `;
    static components = { Dropdown, DropdownItem };
    static props = [];

    setup() {
        super.setup();
        this.action = useService("action");
    }

    openPortal() {
        this.action.doAction({
            type: "ir.actions.act_url",
            url: "/employee-portal",
            target: "self",
        });
    }

    openAction(xmlid) {
        try {
            this.action.doAction(xmlid);
        } catch (error) {
            console.warn("[od19_website] shortcut target unavailable:", xmlid, error);
        }
    }
}

registry.category("systray").add(
    "od19_website.shortcut_menu",
    { Component: ShortcutMenu },
    { sequence: 30 }
);
