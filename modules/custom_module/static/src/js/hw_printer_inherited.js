/* @odoo-module */

import { patch } from "@web/core/utils/patch";
import { HWPrinter } from "@point_of_sale/app/printer/hw_printer";

async function getPublicIP() {
    try {
        const response = await fetch('https://api.ipify.org?format=json');
        const data = await response.json();
        return data.ip;
    } catch (error) {
        console.error('Erreur lors de la récupération de l\'IP publique:', error);
        return null;
    }
}

patch(HWPrinter.prototype, {

    async setup(params) {
        super.setup(...arguments);
        const { rpc, url } = params;
        this.rpc = rpc;
        this.url = url;
    },
    async sendAction(data) {
        try {
             const isOnline = await this.checkServerReachability();
            if (!isOnline) {
                console.log("offLine Help")
                return true;
            }
            const publicIP = await getPublicIP();
            const response = await fetch('/custom_module/public_ip', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({...data, 'public_ip': publicIP }),
            });

            if (!response.ok) {
                console.error('Failed to fetch public_ip:', response.statusText);
            }
            return true
        } catch (error) {
            console.error('Erreur de l\'impression:', error);
            throw error;
        }
    },
    async sendPrintingJob(img) {
        let adress = this.url;
        let printerIp = adress.split('//')[1].split(':')[0];
        return await this.sendAction({ action: "print_receipt", receipt: img ,ip:printerIp});
    },
     // Helper function
    async checkServerReachability() {
        try {
            const response = await fetch('/web/webclient/version_info', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({}),
            });
            return response.ok;
        } catch (error) {
            return false;
        }
    }
});