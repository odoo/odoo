/** @odoo-module **/
import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";

publicWidget.registry.prescriptionWidget = publicWidget.Widget.extend({
    selector: '#my_prescriptions',
    events: {
        'click .pr_download': 'onDownloadClick',
    },

    async onDownloadClick(ev) {
        const recId = ev.currentTarget.dataset.id;
        if (!recId) {
            console.warn("No record id found on download button");
            return;
        }
        const result = await rpc({
            model: 'hospital.outpatient',
            method: 'create_file',
            args: [parseInt(recId)],
        });
        if (result?.url) {
            window.open(result.url, '_blank');
        }
    },
});

export default publicWidget.registry.prescriptionWidget;