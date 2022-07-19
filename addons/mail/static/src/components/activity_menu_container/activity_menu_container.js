/** @odoo-module **/

import ActivityMenu from '@mail/js/systray/systray_activity_menu';

import { ComponentAdapter } from "web.OwlCompatibility";

const { Component } = owl;

class ActivityMenuAdapter extends ComponentAdapter {
    setup() {
        this.env = owl.Component.env;
        super.setup();
    }
}

export class ActivityMenuContainer extends Component {
    get activityMenuWidget() {
        return ActivityMenu;
    }
}


Object.assign(ActivityMenuContainer, {
    components: { ActivityMenuAdapter },
    template: 'mail.ActivityMenuContainer',
});
