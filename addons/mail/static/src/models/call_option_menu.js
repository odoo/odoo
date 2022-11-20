/** @odoo-module **/

import { useComponentToModel } from "@mail/component_hooks/use_component_to_model";
import { one, Model } from "@mail/model";

Model({
    name: "CallOptionMenu",
    template: "mail.CallOptionMenu",
    componentSetup() {
        useComponentToModel({ fieldName: "component" });
    },
    recordMethods: {
        /**
         * Creates and download a file that contains the logs of the current RTC call.
         *
         * @param {MouseEvent} ev
         */
        async onClickDownloadLogs(ev) {
            const channel = this.callActionListView.thread;
            if (!channel.rtc) {
                return;
            }
            const data = window.JSON.stringify(channel.rtc.logs);
            const blob = new window.Blob([data], { type: "application/json" });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `RtcLogs_Channel${channel.id}_Session${
                channel.rtc.currentRtcSession.id
            }_${window.moment().format("YYYY-MM-DD_HH-mm")}.json`;
            a.click();
            window.URL.revokeObjectURL(url);
        },
    },
    fields: {
        callActionListView: one("CallActionListView", {
            related: "popoverViewOwner.callActionListViewOwnerAsMoreMenu",
        }),
        callView: one("CallView", { related: "callActionListView.callView", required: true }),
        popoverViewOwner: one("PopoverView", { identifying: true, inverse: "callOptionMenuView" }),
    },
});
