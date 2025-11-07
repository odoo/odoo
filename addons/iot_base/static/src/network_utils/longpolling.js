import { registry } from '@web/core/registry';
import { post } from '@iot_base/network_utils/http';
import { uuid } from "@web/core/utils/strings";
import { _t } from '@web/core/l10n/translation';

export class IoTLongpolling {
    static serviceDependencies = ["notification", "orm"];
    actionRoute = '/iot_drivers/action';
    pollRoute = '/iot_drivers/event';

    rpcDelay = 1500;
    maxRpcDelay = 15000;

    _retries = 0;
    _listeners = {};

    constructor() {
        this.setup(...arguments);
    }

    /**
     * Setup in addition to constructor to allow patching
     */
    setup({ notification, orm }) {
        this._session_id = uuid();
        this._delayedStartPolling(this.rpcDelay);
        this.notification = notification;
        this.orm = orm;
    }

    /**
     * Add a device_identifier to listeners[iot_ip] and restart polling
     *
     * @param {string} iot_ip
     * @param {Array} devices list of devices
     * @param {string} listener_id
     * @param {boolean} fallback if true, no notification will be displayed on fail
     * @param {Callback} callback
     */
    async addListener(iot_ip, devices, listener_id, callback, fallback = true) {
        if (!this._listeners[iot_ip]) {
            this._listeners[iot_ip] = {
                last_event: 0,
                devices: {},
                session_id: this._session_id,
                abortController: null,
            };
        }
        for (const device of devices) {
            this._listeners[iot_ip].devices[device] = {
                listener_id: listener_id,
                device_identifier: device,
                callback: callback,
            };
        }
        this.stopPolling(iot_ip);
        this.startPolling(iot_ip, fallback);
    }

    /**
     * Stop listening to iot device with id `device_identifier`
     * @param {string} iot_ip
     * @param {string} device_identifier
     * @param {string} listener_id
     */
    removeListener(iot_ip, device_identifier, listener_id) {
        const device = this._listeners[iot_ip].devices[device_identifier];
        if (device && device.listener_id === listener_id) {
            delete this._listeners[iot_ip].devices[device_identifier];
        }
    }

    /**
     * Execute an action on device_identifier
     * Action depends on the driver that supports the device
     *
     * @param {string} iot_ip
     * @param {string} device_identifier
     * @param {Object} data contains the information needed to perform an action on this device_identifier
     * @param {boolean} fallback if true, no notification will be displayed on fail
     * @param {string} route endpoint to call on the IoT Box (default: /iot_drivers/action)
     */
    action(iot_ip, device_identifier, data, fallback = false, route = null) {
        this.protocol = window.location.protocol;
        const body = {
            session_id: this._session_id,
            device_identifier: device_identifier,
            data,
        };
        return this._rpcIoT(iot_ip, route || this.actionRoute, body, undefined, fallback);
    }

    /**
     * Start a long polling, i.e. it continually opens a long poll
     * connection as long as it is not stopped (@see `stopPolling`)
     * @param {string} iot_ip
     * @param {boolean} fallback if true, no notification will be displayed on fail
     */
    startPolling(iot_ip, fallback = true) {
        if (iot_ip) {
            if (!this._listeners[iot_ip].abortController) {
                this._poll(iot_ip, fallback);
            }
        } else {
            const self = this;
            Object.keys(this._listeners).forEach((ip) => {
                self.startPolling(ip);
            });
        }
    }

    /**
     * Stops any started long polling
     *
     * Aborts a pending long-poll so that we immediately remove ourselves
     * from listening on notifications on this channel.
     */
    stopPolling(iot_ip) {
        if (this._listeners[iot_ip].abortController) {
            this._listeners[iot_ip].abortController.abort();
            this._listeners[iot_ip].abortController = null;
        }
    }

    _delayedStartPolling(delay) {
        // ``fallback: true`` to avoid error notification on longpolling setup
        setTimeout(() => this.startPolling(null, true), delay);
    }

    /**
     * Execute an RPC to the box
     * Used to do both polling or action
     *
     * @param {string} iot_ip IP of the IoT Box
     * @param {string} route endpoint to call on the IoT Box
     * @param {Object} params information needed to perform an action or the listener for the polling
     * @param {number} timeout time before the request times out (undefined to use default timeout from http.js)
     * @param {boolean} fallback if true, no notification will be displayed on fail
     * @param {Object} headers headers to send with the request (optional, allows patching)
     */
    async _rpcIoT(iot_ip, route, params, timeout = undefined, fallback = false, headers = undefined) {
        try {
            const abortController = new AbortController();

            if (this._listeners[iot_ip] && route === this.pollRoute) {
                this._listeners[iot_ip].abortController = abortController;
            }
            return await post(iot_ip, route, params, timeout, headers, abortController.signal);
        } catch (error) {
            if (!fallback && error?.name !== "AbortError") {
                this._doWarnFail(iot_ip);
            }
            throw new Error("Longpolling action failed");
        }
    }

    /**
     * Make a poll request to an IoT Box
     *
     * @param {string} iot_ip
     * @param {boolean} fallback if true, no notification will be displayed on fail
     */
    _poll(iot_ip, fallback = true) {
        const listener = this._listeners[iot_ip];

        // The backend has a maximum cycle time of 50 seconds so give +10 seconds
        this._rpcIoT(iot_ip, this.pollRoute, { listener: listener }, 60000, fallback).then(
            (result) => {
                this._retries = 0;
                this._listeners[iot_ip].abortController = null;
                const remainingDevices = Object.keys(this._listeners[iot_ip].devices || {});
                if (result.result) {
                    if (this._session_id === result.result.session_id) {
                        this._onSuccess(iot_ip, result.result);
                    }
                } else if (remainingDevices.length > 0) {
                    this._poll(iot_ip);
                }
            },
            (e) => {
                if (e.name === "TimeoutError") {
                    this._onError();
                }
            }
        );
    }

    _onSuccess(iot_ip, result) {
        this._listeners[iot_ip].last_event = result.time;

        const devices = this._listeners[iot_ip].devices;
        devices[result.device_identifier]?.callback(result);

        if (Object.keys(devices || {}).length > 0) {
            this._poll(iot_ip);
        }
        this._retries = 0;
    }

    _onError() {
        this._retries++;
        this._delayedStartPolling(Math.min(this.rpcDelay * this._retries, this.maxRpcDelay));
    }

    /**
     * This method is needed in _poll.
     * @param {string} url
     */
    _doWarnFail(url) {
        this.notification.add(
            _t("Failed to reach IoT Box at %s", url),
            {
                title: _t("Connection to IoT Box failed"),
                type: "danger",
            }
        );
    }
}

export const iotLongpollingService = {
    dependencies: IoTLongpolling.serviceDependencies,
    start(_, deps) {
        return new IoTLongpolling(deps);
    },
};

registry.category('services').add('iot_longpolling', iotLongpollingService);
