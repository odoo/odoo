/** @odoo-module **/

import { formView } from "@web/views/form/form_view";
import { FormController } from "@web/views/form/form_controller";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { useSubEnv, onMounted, onWillUnmount } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";


export class AddIoTBoxFormController extends FormController {
    setup() {
        super.setup();
        this.notification = useService("notification");
        this.orm = useService("orm");
        this.onClickViewButton = this.env.onClickViewButton;
        this.iotBoxesBeforeConnection = [];
        this.successNotification = null;    // Notification to show when a new IoT box is found
        this.iotCheckTimer = null;          // Timer to manage polling

        useSubEnv({ onClickViewButton: this.onClickButtonAddIoT.bind(this) });

        onMounted(async () => {
            this.pairButtonRef = this.rootRef.el.querySelector("#pair_button");
            await this.initializeIoTConnection();
        });

        onWillUnmount(() => {
            if (this.iotCheckTimer) {
                clearInterval(this.iotCheckTimer);
            }
            this.closeConnectingNotification?.();
        });
    }

    /**
     * Creates a loop to check for new IoT Boxes every 10 seconds.
     * @returns {Promise<void>}
     */
    async initializeIoTConnection() {
        this.iotBoxesBeforeConnection = await this.orm.call("iot.box", "search_read", [[], ["identifier"]]);

        this.closeConnectingNotification = this.notification.add(
            _t("We're looking for your IoT Box"),
            {
                type: "info",
                sticky: true,
            }
        );

        // Set a timer to check for new IoT Boxes every 10 seconds
        this.iotCheckTimer = setInterval(async () => {
            if (await this.lookForNewIoTBox()) {
                this.notifyIoTBoxFound(true);
            }
        }, 10000);

        // Set a timeout to stop the polling after 10 minutes
        setTimeout(() => this.notifyIoTBoxFound(false), 60 * 10000);
    }

    /**
     * Override the default behavior of the button callback.
     * If the 'Cancel' button is pressed, notify if any new IoT box was found
     * before closing.
     * If the 'Pair' button is pressed and succeeds, disable the button
     * to prevent an error on subsequent clicks.
     * @param params {Object} The params object passed to the button callback.
     * @returns {Promise<void>}
     */
    async onClickButtonAddIoT(params) {
        if (!params.clickParams.name || params.clickParams.name !== "box_pairing") {
            this.notifyIoTBoxFound(await this.lookForNewIoTBox());
        }
        await this.onClickViewButton(params);
        if (params.clickParams.name === "box_pairing") {
            this.pairButtonRef.setAttribute("disabled", "true");
        }
    }

    /**
     * Look for new IoT Boxes that have been connected since the last check.
     * @returns {Promise<boolean>} True if a new IoT Box has been found, false otherwise.
     */
    async lookForNewIoTBox() {
        const iotBoxesAfterConnection = await this.orm.call("iot.box", "search_read", [[], ["identifier"]]);
        const newIoTBoxes = iotBoxesAfterConnection.filter(
            afterBox => !this.iotBoxesBeforeConnection.some(
                beforeBox => beforeBox.identifier === afterBox.identifier
            )
        );

        return newIoTBoxes.length > 0;
    }

    /**
     * Notify the user if a new IoT Box has been found. If no new IoT Box has been found, notify the user.
     * @param {boolean} found Whether a new IoT Box has been found.
     */
    notifyIoTBoxFound(found) {
        this.closeConnectingNotification?.();
        if (found && !this.successNotification) {
            this.env.services.action.doAction({ type: "ir.actions.act_window_close" });
            this.notification.add(_t("New IoT Box connected!"), { type: "success" });
        } else {
            this.notification.add(_t("No new IoT Box found."), { type: "warning" });
        }
    }
}

export const addIoTBox = { ...formView, Controller: AddIoTBoxFormController };

registry.category("views").add('add_iot_box_wizard', addIoTBox);
