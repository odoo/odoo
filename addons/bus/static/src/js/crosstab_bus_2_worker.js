
onconnect = ev => this.manager.updatePort(ev.ports[0]);

if (!this.manager) {

    class Manager {

        constructor() {
            this._channels = [];
            this._masterTabId = null;
            this._options = {};
            this._tabs = [];
        }

        /**
         * @param {MessagePort} port
         */
        updatePort(port) {
            this._port = port;
            this._port.onmessage = ev => this._onMessage(ev);
        }

        /**
         * @private
         * @param {MessageEvent} ev
         * @param {Array} ev.data
         * @param {string} ev.data[0] name of event
         * @param {...any} [ev.data[1..n]]
         */
        _onMessage(ev) {
            const type = ev.data[0];
            const args = ev.data.slice(1);
            switch (type) {
                case 'tab:add-channel':
                    this._onMessageTabAddChannel(...args);
                    break;
                case 'tab:delete-channel':
                    this._onMessageTabDeleteChannel(...args);
                    break;
                case 'tab:focus':
                    this._onMessageTabFocus(...args);
                    break;
                case 'tab:last-presence':
                    this._onMessageTabLastPresence(...args);
                    break;
                case 'tab:notifications':
                    this._onMessageTabNotifications(...args);
                    break;
                case 'tab:register':
                    this._onMessageTabRegister(...args);
                    break;
                case 'tab:update-option':
                    this._onMessageTabUpdateOption(...args);
                    break;
                case 'tab:unregister':
                    this._onMessageTabUnregister(...args);
                    break;
            }
        }

        /**
         * @private
         * @param {string} channel
         */
        _onMessageTabAddChannel(channel) {
            if (this._channels.includes(channel)) {
                return;
            }
            this._channels.push(channel);
            this._port.postMessage(['worker:add-channel', channel]);
        }

        /**
         * @private
         * @param {string} channel
         */
        _onMessageTabDeleteChannel(channel) {
            if (!this._channels.includes(channel)) {
                return;
            }
            this._channels = this._channels.filter(ch => ch !== channel);
            this._port.postMessage(['worker:delete-channel', channel]);
        }

        /**
         * @private
         * @param {boolean} focus
         */
        _onMessageTabFocus(focus) {
            this._port.postMessage(['worker:focus', focus]);
        }

        /**
         * @private
         * @param {integer} lastPresenceTime
         */
        _onMessageTabLastPresence(lastPresenceTime) {
            this._lastPresenceTime = Math.max(this._lastPresenceTime, lastPresenceTime);
            this._port.postMessage(['worker:last-presence', this._lastPresenceTime]);
        }

        /**
         * @private
         * @param {Object[]} notifications
         */
        _onMessageTabNotifications(notifications) {
            this._port.postMessage(['worker:notifications', notifications]);
        }

        /**
         * @private
         * @param {string} tabId
         */
        _onMessageTabRegister(tabId) {
            if (this._tabs.includes(tabId)) {
                return;
            }
            this._tabs.push(tabId);
            this._port.postMessage(['worker:channels', this._channels, tabId]);
            this._port.postMessage(['worker:options', this._options, tabId]);
            if (this._tabs.length === 1) {
                this._masterTabId = tabId;
                this._port.postMessage(['worker:master', tabId]);
            }
            this._port.postMessage(['worker:registered', tabId]);
        }

        /**
         * @private
         * @param {string} key
         * @param {any} value
         */
        _onMessageTabUpdateOption(key, value) {
            if (this._options[key] === value) {
                return;
            }
            this._options[key] = value;
            this._port.postMessage(['worker:update-option', key, value]);
        }

        /**
         * @private
         * @param {string} tabId
         */
        _onMessageTabUnregister(tabId) {
            if (!this._tabs.includes(tabId)) {
                return;
            }
            this._tabs = this._tabs.filter(tab => tab !== tabId);
            if (tabId === this._masterTabId) {
                this._masterTabId = null;
            }
            if (this._tabs.length > 0) {
                this._masterTabId = this._tabs[0];
                this._port.postMessage(['worker:master', this._tabs[0]]);
            }
        }
    }

    this.manager = new Manager();
}