import { registry } from "@web/core/registry";
import { post } from "@iot_base/network_utils/http";
import { _t } from "@web/core/l10n/translation";

/**
 * Class to handle IoT actions
 * The class is used to send actions to IoT devices and handle fallbacks
 * in case the request fails: it will try to send the request using
 * HTTP POST method and then using the websocket.
 */
export class IotAction {
    constructor() {
        this.setup(...arguments);
    }

    /**
     * @param {import("@iot_base/network_utils/longpolling").IotLongpolling} longpolling Longpolling service
     * @param notification Notification service
     * @param orm ORM service
     */
    setup({ iot_longpolling, notification, orm }) {
        this.longpolling = iot_longpolling;
        this.notification = notification;
        this.orm = orm;
    }

    defaultOnFailure(_message, deviceIdentifier, _messageId) {
        this.notification.add(_t("Failed to reach the device: %s", deviceIdentifier), { type: "danger" });
    }

    /**
     * Generates the list of connection methods to try, in order.
     * Defined as a separate method to allow patching.
     */
    _getConnectionTypes(ip, _identifier, deviceIdentifier, data, onSuccess, onFailure) {
        return [
            async () => {
                this.longpolling.onMessage(ip, deviceIdentifier, onSuccess, onFailure);
                await this.longpolling.sendMessage(ip, { device_identifier: deviceIdentifier, data }, null, true);
            },
        ];
    }

    /**
     * Call for an action method on the IoT Box
     * @param iotBoxId IoT Box record ID
     * @param deviceIdentifier Identifier of the device connected to the IoT Box
     * @param data Data to send
     * @param onSuccess Callback to run when a message is received (optional)
     * @param onFailure Callback to run when the request fails (optional)
     * @returns {Promise<void>}
     */
    async action(
        iotBoxId,
        deviceIdentifier,
        data,
        onSuccess = (_message, _deviceIdentifier, _operationId) => {},
        onFailure = (_message, deviceIdentifier, messageId) => this.defaultOnFailure(deviceIdentifier, messageId),
    ) {
        if (!["number", "string"].includes(typeof iotBoxId)) {
            iotBoxId = iotBoxId[0]; // iotBoxId is the ``Many2one`` field, we need the actual ID
        }
        const [{ ip, identifier }] = await this.orm.searchRead("iot.box", [["id", "=", iotBoxId]], ["ip", "identifier"]);

        // Define the connection types in the order of executions to try
        const connectionTypes = this._getConnectionTypes(
            ip,
            identifier,
            deviceIdentifier,
            data,
            onSuccess,
            onFailure
        )

        // Try to send the request using the connection types
        for (const connectionType of connectionTypes) {
            try {
                return await connectionType();
            } catch (e) {
                console.debug("IoT Box action: attempted method failed, attempting another protocol.", e);
            }
        }

        // If all the connection types failed, run the onFailure callback
        onFailure({ status: "disconnected" }, deviceIdentifier);
    }
}


export const iotHttpService = {
    dependencies: ["notification", "orm", "iot_longpolling"],
    start(env) {
        return this.availableMethods(env.services);
    },
    availableMethods(services) {
        const longpolling = {
            sendMessage: services.iot_longpolling.sendMessage.bind(services.iot_longpolling),
            onMessage: services.iot_longpolling.onMessage.bind(services.iot_longpolling),
        };

        const iotAction = new IotAction(services);
        const action = iotAction.action.bind(iotAction);

        // Expose only these functions to the environment
        return { post, action, longpolling };
    },
};

registry.category("services").add("iot_http", iotHttpService);
