/** @odoo-module **/

import { registry } from '@web/core/registry';
import { IoTConnectionErrorDialog } from './iot_connection_error_dialog';

export class IoTLongpolling {
    static serviceDependencies = ["dialog"];
    constructor() {
        this.setup(...arguments);
    }
    // setup to allow patching
    async setup({ dialog }) {
        // CONSTANTS
        this.POLL_TIMEOUT = 60000;
        this.POLL_ROUTE = '/hw_drivers/event';
        this.ACTION_TIMEOUT = 6000;
        this.ACTION_ROUTE = '/hw_drivers/action';

        this.RPC_DELAY = 1500;
        this.MAX_RPC_DELAY = 1500 * 10;

        // PROPERTIES
        this._retries = 0;

        this._session_id = this._createUUID();
        this._listeners = {};
        this._delayedStartPolling(this.RPC_DELAY);
        this.dialogService = dialog;
        this.useLna = false;
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Add a device_identifier to listeners[iot_ip] and restart polling
     *
     * @param {String} iot_ip
     * @param {Array} devices list of devices
     * @param {String} listener_id
     * @param {Boolean} fallback if true, no `IoTConnectionErrorDialog` popup will be displayed on fail
     * @param {Callback} callback
     */
    addListener(iot_ip, devices, listener_id, callback, fallback = false) {
        if (!this._listeners[iot_ip]) {
            this._listeners[iot_ip] = {
                last_event: 0,
                devices: {},
                session_id: this._session_id,
                abortController: null,
            };
        }
        for (const device in devices) {
            this._listeners[iot_ip].devices[devices[device]] = {
                listener_id: listener_id,
                device_identifier: devices[device],
                callback: callback,
            };
        }
        this.stopPolling(iot_ip);
        this.startPolling(iot_ip, fallback);
        return Promise.resolve();
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
     * @param {String} iot_ip
     * @param {String} device_identifier
     * @param {Object} data contains the information needed to perform an action on this device_identifier
     */
    action(iot_ip, device_identifier, data) {
        var data = {
            params: {
                session_id: this._session_id,
                device_identifier: device_identifier,
                data: JSON.stringify(data),
            }
        };
        var options = {
            timeout: this.ACTION_TIMEOUT,
        };
        return this._rpcIoT(iot_ip, this.ACTION_ROUTE, data, options);
    }

    /**
     * Start a long polling, i.e. it continually opens a long poll
     * connection as long as it is not stopped (@see `stopPolling`)
     * @param {String} iot_ip
     * @param {Boolean} fallback if true, no `IoTConnectionErrorDialog` popup will be displayed on fail
     */
    startPolling(iot_ip, fallback = false) {
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
     * Aborts a pending longpoll so that we immediately remove ourselves
     * from listening on notifications on this channel.
     */
    stopPolling(iot_ip) {
        if (this._listeners[iot_ip].abortController) {
            this._listeners[iot_ip].abortController.abort();
            this._listeners[iot_ip].abortController = null;
        }
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _delayedStartPolling(delay) {
        const self = this;
        setTimeout(function () {
            self.startPolling(null);
        }, delay);
    }

    _createUUID() {
        var s = [];
        var hexDigits = "0123456789abcdef";
        for (var i = 0; i < 36; i++) {
            s[i] = hexDigits.substr(Math.floor(Math.random() * 0x10), 1);
        }
        s[14] = "4";  // bits 12-15 of the time_hi_and_version field to 0010
        s[19] = hexDigits.substr((s[19] & 0x3) | 0x8, 1);  // bits 6-7 of the clock_seq_hi_and_reserved to 01
        s[8] = s[13] = s[18] = s[23] = "-";
        return s.join("");
    }

    formatEndpoint(ip, route, forceHttp = false) {
        const protocol = forceHttp ? "http:" : window.location.protocol;
        const rawIp = forceHttp ? ip.replace(/^(\d+)-(\d+)-(\d+)-(\d+).*/, "$1.$2.$3.$4") : ip;
        const url = new URL(`${protocol}//${rawIp}`);
        url.pathname = route;
        return url.toString();
    }

    /**
     * Execute a RPC to the box
     * Used to do polling or an action
     *
     * @param {String} iot_ip
     * @param {String} route
     * @param {Object} data information needed to perform an action or the listener for the polling
     * @param {Object} options.timeout
     */
    async _rpcIoT(iot_ip, route, data, options) {
        const url = this.formatEndpoint(iot_ip, route, this.useLna);
        const requestParams = {
            method: "POST",
            body: JSON.stringify(data),
            headers: {
                "Content-Type": "application/json;charset=utf-8",
            },
            targetAddressSpace: this.useLna ? "local" : undefined,
        };
        const abortController = new AbortController();
        if (options.timeout) {
            requestParams.signal = AbortSignal.any([AbortSignal.timeout(options.timeout), abortController.signal]);
        } else {
            requestParams.signal = abortController.signal;
        }

        if (this._listeners[iot_ip] && route === '/hw_drivers/event') {
            this._listeners[iot_ip].abortController = abortController;
        }

        const response = await fetch(url, requestParams);
        return await response.json();
    }

    /**
     * Make a request to an IoT Box
     *
     * @param {String} iot_ip
     * @param {Boolean} fallback if true, no `IoTConnectionErrorDialog` popup will be displayed on fail
     */
    _poll(iot_ip, fallback = false) {
        var listener = this._listeners[iot_ip];
        var data = {
            params: {
                listener: listener,
            }
        };
        var options = {
            timeout: this.POLL_TIMEOUT,
        };

        // The backend has a maximum cycle time of 50 seconds so give +10 seconds
        this._rpcIoT(iot_ip, this.POLL_ROUTE, data, options).then(
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
                if (e.name === "AbortError") {
                    return;
                }
                if (e.name === "TimeoutError") {
                    this._onError();
                } else if (!fallback) {
                    this._doWarnFail(iot_ip);
                }
            }
        );
    }

    _onSuccess(iot_ip, result) {
        this._listeners[iot_ip].last_event = result.time;

        var devices = this._listeners[iot_ip].devices;
        if (devices[result.device_identifier]) {
            devices[result.device_identifier].callback(result);
        }
        if (Object.keys(devices || {}).length > 0) {
            this._poll(iot_ip);
        }
        this._retries = 0;
    }

    _onError() {
        this._retries++;
        this._delayedStartPolling(Math.min(this.RPC_DELAY * this._retries, this.MAX_RPC_DELAY));
    }

    /**
     * This method is needed in _poll.
     * @param {string} url
     */
    _doWarnFail(url) {
        this.dialogService.add(IoTConnectionErrorDialog, { href: url });
    }

    /**
     * Enable/disable using Local Network Access.
     * This forces HTTP on all IoT requests.
     * @param {boolean} isLnaEnabled
     */
    setLna(isLnaEnabled) {
        this.useLna = isLnaEnabled;
    }
}

export const iotLongpollingService = {
    dependencies: IoTLongpolling.serviceDependencies,
    start(_, deps) {
        return new IoTLongpolling(deps);
    },
};

registry.category('services').add('iot_longpolling', iotLongpollingService);
