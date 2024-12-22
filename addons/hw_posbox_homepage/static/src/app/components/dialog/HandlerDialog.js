/* global owl */

import useStore from "../../hooks/useStore.js";
import { BootstrapDialog } from "./BootstrapDialog.js";
import { LoadingFullScreen } from "../LoadingFullScreen.js";

const { Component, xml, useState } = owl;

export class HandlerDialog extends Component {
    static props = {};
    static components = { BootstrapDialog, LoadingFullScreen };

    setup() {
        this.store = useStore();
        this.state = useState({
            initialization: true,
            waitRestart: false,
            loading: false,
            handlerData: {},
            globalLogger: {},
        });
    }

    onClose() {
        this.state.initialization = [];
        this.state.handlerData = {};
    }

    async getHandlerData() {
        try {
            const data = await this.store.rpc({
                url: "/hw_posbox_homepage/log_levels",
            });
            this.state.handlerData = data;
            this.state.globalLogger = {
                "iot-logging-root": data.root_logger_log_level,
                "iot-logging-odoo": data.odoo_current_log_level,
            };
            this.state.initialization = false;
        } catch {
            console.warn("Error while fetching data");
        }
    }

    async onChange(name, value) {
        try {
            await this.store.rpc({
                url: "/hw_posbox_homepage/log_levels_update",
                method: "POST",
                params: {
                    name: name,
                    value: value,
                },
            });
        } catch {
            console.warn("Error while saving data");
        }
    }

    async loadIotHandlers() {
        try {
            const data = await this.store.rpc({
                url: "/hw_posbox_homepage/load_iot_handlers",
            });

            if (data.status === "success") {
                this.state.waitRestart = true;
            }
        } catch {
            console.warn("Error while saving data");
        }
    }

    async clearIotHandlers() {
        try {
            const data = await this.store.rpc({
                url: "/hw_posbox_homepage/clear_iot_handlers",
            });

            if (data.status === "success") {
                this.state.waitRestart = true;
            }
        } catch {
            console.warn("Error while saving data");
        }
    }

    static template = xml`
        <LoadingFullScreen t-if="this.state.waitRestart">
            <t t-set-slot="body">
                Processing your request, please wait...
            </t>
        </LoadingFullScreen>

        <BootstrapDialog identifier="'handler-configuration'" btnName="'Log level'" onOpen.bind="getHandlerData" onClose.bind="onClose">
            <t t-set-slot="header">
                Handler logging
            </t>
            <t t-set-slot="body">
                <div t-if="this.state.initialization" class="position-absolute top-0 start-0 bg-white h-100 w-100 justify-content-center align-items-center d-flex flex-column gap-3" style="z-index: 9999; min-height: 300px">
                    <div class="spinner-border" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <p>Currently scanning for initialized drivers and interfaces...</p>
                </div>
                <t t-else="">
                    <div class="mb-3">
                        <h5>Global logs level</h5>
                        <div class="form-check mb-3">
                            <input name="log-to-server"
                                id="log-to-server"
                                class="form-check-input cursor-pointer"
                                type="checkbox"
                                t-att-checked="this.state.handlerData.is_log_to_server_activated"
                                t-on-change="(ev) => this.onChange(ev.target.name, ev.target.checked)" />
                            <label class="form-check-label cursor-pointer" for="log-to-server">IoT logs automatically send to server logs</label>
                        </div>
                        <div t-foreach="Object.entries(this.state.globalLogger)" t-as="global" t-key="global[0]" class="input-group input-group-sm mb-3">
                            <label class="input-group-text w-50" t-att-for="global[0]" t-esc="global[0]" />
                            <select t-att-name="global[0]"
                                t-if="global[1]"
                                class="form-select"
                                t-on-change="(ev) => this.onChange(ev.target.name, ev.target.value)"
                                t-att-id="global[0]"
                                t-att-value="global[1]">
                                <option value="parent">Same as Odoo</option>
                                <option value="info">Info</option>
                                <option value="debug">Debug</option>
                                <option value="warning">Warning</option>
                                <option value="error">Error</option>
                            </select>
                            <input t-else="" type="text" class="form-control" aria-label="Text input with dropdown button" disabled="true" placeholder="Logger uninitialised" />
                        </div>
                    </div>
                    <div class="mb-3">
                        <h5>Interfaces logs level</h5>
                        <div t-foreach="Object.entries(this.state.handlerData.interfaces_logger_info)" t-as="interface" t-key="interface[0]" class="input-group input-group-sm mb-3">
                            <label class="input-group-text w-50" t-att-for="interface[0]" t-esc="interface[0]" />
                            <select t-att-name="'iot-logging-interface-'+interface[0]"
                                t-if="interface[1]"
                                class="form-select"
                                t-on-change="(ev) => this.onChange(ev.target.name, ev.target.value)"
                                t-att-id="interface[0]"
                                t-att-value="interface[1].is_using_parent_level ? 'parent' : interface[1].level">
                                <option value="parent">Same as Odoo</option>
                                <option value="info">Info</option>
                                <option value="debug">Debug</option>
                                <option value="warning">Warning</option>
                                <option value="error">Error</option>
                            </select>
                            <input t-else="" type="text" class="form-control" aria-label="Text input with dropdown button" disabled="true" placeholder="Logger uninitialised" />
                        </div>
                    </div>
                    <div class="mb-3">
                        <h5>Drivers logs level</h5>
                        <div t-foreach="Object.entries(this.state.handlerData.drivers_logger_info)" t-as="drivers" t-key="drivers[0]" class="input-group input-group-sm mb-3">
                            <label class="input-group-text w-50" t-att-for="drivers[0]" t-esc="drivers[0]" />
                            <select t-att-name="'iot-logging-driver-'+drivers[0]"
                                t-if="drivers[1]"
                                class="form-select"
                                t-on-change="(ev) => this.onChange(ev.target.name, ev.target.value)"
                                t-att-id="drivers[0]"
                                t-att-value="drivers[1].is_using_parent_level ? 'parent' : drivers[1].level">
                                <option value="parent">Same as Odoo</option>
                                <option value="info">Info</option>
                                <option value="debug">Debug</option>
                                <option value="warning">Warning</option>
                                <option value="error">Error</option>
                            </select>
                            <input t-else="" type="text" class="form-control" aria-label="Text input with dropdown button" disabled="true" placeholder="Logger uninitialised" />
                        </div>
                    </div>
                    <div>
                        <h5>Debug</h5>
                        <div class="d-flex gap-2">
                            <button class="btn btn-primary btn-sm" t-on-click="loadIotHandlers">
                                Load IOT Handlers
                            </button>
                            <button class="btn btn-primary btn-sm" t-on-click="clearIotHandlers">
                                Clear IOT Handlers
                            </button>
                        </div>
                    </div>
                </t>
            </t>
            <t t-set-slot="footer">
                <button type="button" class="btn btn-primary btn-sm" data-bs-dismiss="modal">Close</button>
            </t>
        </BootstrapDialog>
    `;
}
