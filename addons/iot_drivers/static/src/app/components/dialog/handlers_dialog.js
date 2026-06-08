/* global owl */

import useStore from "../../hooks/store_hook.js";
import { Dialog } from "./dialog.js";
import { LoadingFullScreen } from "../loading_full_screen.js";

const { Component, xml, signal } = owl;

export class HandlerDialog extends Component {
    static components = { Dialog, LoadingFullScreen };

    store = useStore();

    initialization = signal(true);
    waitRestart = signal(false);
    loading = signal(false);
    handlerData = signal({});
    globalLogger = signal({});

    onClose() {
        this.initialization.set([]);
        this.handlerData.set({});
    }

    async getHandlerData() {
        try {
            const data = await this.store.rpc({
                url: "/iot_drivers/log_levels",
            });
            this.handlerData.set(data);
            this.globalLogger.set({
                "iot-logging-root": data.root_logger_log_level,
                "iot-logging-odoo": data.odoo_current_log_level,
            });
            this.initialization.set(false);
        } catch {
            console.warn("Error while fetching data");
        }
    }

    async onChange(name, value) {
        try {
            await this.store.rpc({
                url: "/iot_drivers/log_levels_update",
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

    async enableCustomHandlers(value) {
        this.waitRestart.set(!value);
        try {
            await this.store.rpc({
                url: "/iot_drivers/enable_custom_handlers",
                method: "POST",
                params: {
                    enable: value,
                },
            });
        } catch {
            console.warn("Error while enabling custom handlers");
        }
    }

    static template = xml`
    <t t-translation="off">
        <LoadingFullScreen t-if="this.waitRestart()">
            <t t-set-slot="body">
                Processing your request, please wait...
            </t>
        </LoadingFullScreen>

        <Dialog name="'Handlers Configuration'" btnName="'Handlers Configuration'" onOpen.bind="this.getHandlerData" onClose.bind="this.onClose">
            <t t-set-slot="body">
                <div t-if="this.initialization()" class="position-absolute top-0 start-0 bg-white h-100 w-100 justify-content-center align-items-center d-flex flex-column gap-3 always-on-top handler-loading">
                    <div class="spinner-border" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <p>Currently scanning for initialized drivers and interfaces...</p>
                </div>
                <t t-else="">
                    <div class="mb-3">
                        <h5>Custom Handlers</h5>
                        <div class="form-check mb-3">
                            <input name="custom-handler"
                                id="custom-handlers"
                                class="form-check-input cursor-pointer"
                                type="checkbox"
                                t-att-checked="this.handlerData().is_custom_handlers_enabled"
                                t-on-change="(ev) => this.enableCustomHandlers(ev.target.checked)" />
                            <label class="form-check-label cursor-pointer" for="custom-handlers">Download custom handlers from the database</label>
                        </div>
                    </div>
                    <div class="mb-3">
                        <h5>Global logs level</h5>
                        <div t-foreach="Object.entries(this.globalLogger())" t-as="global" t-key="global[0]" class="input-group input-group-sm mb-3">
                            <label class="input-group-text w-50" t-att-for="global[0]" t-out="global[0]" />
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
                        <div t-foreach="Object.entries(this.handlerData().interfaces_logger_info)" t-as="interface" t-key="interface[0]" class="input-group input-group-sm mb-3">
                            <label class="input-group-text w-50" t-att-for="interface[0]" t-out="interface[0]" />
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
                        <div t-foreach="Object.entries(this.handlerData().drivers_logger_info)" t-as="drivers" t-key="drivers[0]" class="input-group input-group-sm mb-3">
                            <label class="input-group-text w-50" t-att-for="drivers[0]" t-out="drivers[0]" />
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
                </t>
            </t>
            <t t-set-slot="footer">
                <button type="button" class="btn btn-primary btn-sm" data-bs-dismiss="modal">Close</button>
            </t>
        </Dialog>
    </t>
    `;
}
