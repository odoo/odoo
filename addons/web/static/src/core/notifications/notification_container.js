/** @odoo-module **/

import { Notification as NotificationComponent } from "./notification";

const { Component, tags } = owl;

export class NotificationContainer extends Component {
    setup() {
        this.notifications = [];
        this.props.bus.on("ADD", this, this.add);
        this.props.bus.on("REMOVE", this, this.remove);
    }
    __destroy() {
        this.props.bus.off("ADD", this, this.add);
        this.props.bus.off("REMOVE", this, this.remove);
        super.__destroy();
    }

    /**
     * @param {Object} params
     * @param {number} params.id
     * @param {{
     *      name: string;
     *      icon?: string;
     *      primary?: boolean;
     *      onClick: () => void
     * }[]} params.buttons
     * @param {string} params.className
     * @param {string} params.message
     * @param {boolean} params.messageIsHtml
     * @param {() => void} params.onClose
     * @param {string} params.title
     * @param {"warning" | "danger" | "success" | "info"} params.type
     */
    add(params) {
        const { id, ...props } = params;
        this.notifications.push({ id, props });
        this.render();
    }
    /**
     * @param {number} id
     */
    remove(id) {
        const index = this.notifications.findIndex((n) => n.id === id);
        if (index > -1) {
            this.notifications.splice(index, 1);
            this.render();
        }
    }
}

NotificationContainer.template = tags.xml`
    <div class="o_notification_manager">
        <t t-foreach="notifications" t-as="notification" t-key="notification.id">
            <NotificationComponent
                t-props="notification.props"
                t-transition="o_notification_fade"
                t-on-close="remove(notification.id)"
            />
        </t>
    </div>`;
NotificationContainer.components = { NotificationComponent };
