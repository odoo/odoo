/** @odoo-module **/

import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser"

export class IotWebsocket {
    
    jobs = {};
    
    constructor(bus_service, notification, orm) {
        this.notification = notification;
        this.bus_service = bus_service;
        this.orm = orm;
    }
    
    async getDevicesFromIds(stored_content) {
        return(await this.orm.call("ir.actions.report", "get_devices_from_ids", [0, stored_content]));
    }
    
    async addJob(stored_content, args) {
        const id = args[3];
        let response = await this.getDevicesFromIds(stored_content);
        this.jobs[id] = response;
        setTimeout(() => {
            if (this.jobs[id].length != 0) {
                for (let device in this.jobs[id]) {
                    this.notification.add("Check if the printer is still connected", {
                        title: ("Connection to printer failed " + this.jobs[id][device]["name"]),
                        type: "danger",
                    });
                }
            }
            delete this.jobs[id];
        }, 10000)
        await this.orm.call("ir.actions.report", "render_and_send", [args[0], response, args[1], args[2], args[3]]);
    }
        
        setJobInLocalStorage(value, args) {
            let links = JSON.parse(browser.localStorage.getItem("odoo-iot-linked_reports"))
            if (links === null || typeof links !== 'object')
                links = {}
            links[args[0]] = value
            browser.localStorage.setItem("odoo-iot-linked_reports", JSON.stringify(links))
            this.addJob(value, args);
        }
    }
    
    
export const IotWebsocketService = {
            dependencies: ["bus_service", "notification", "orm"],
            
            async start(env, {bus_service, notification, orm}) {
                let ws = new IotWebsocket(bus_service, notification, orm)
                const iot_channel = await orm.call("iot.channel", "get_iot_channel", [0]);
                if (iot_channel)
                {
                    bus_service.addChannel(iot_channel);
                    bus_service.addEventListener("notification", async (message) => {
                        for (let i in message['detail']) {
                            if (message['detail'][i]['type'] == "print_confirmation" && ws.jobs[message['detail'][i]['payload']['print_id']]) {
                                const deviceId = message['detail'][i]['payload']['device_identifier'];
                                const printId = message['detail'][i]['payload']['print_id'];
                                delete ws.jobs[printId][ws.jobs[printId].findIndex(element => element && element['identifier'] == deviceId)];
                            }
                        }    
                    })
                }
        return ws;
    },
}

registry.category("services").add("iot_websocket", IotWebsocketService);
