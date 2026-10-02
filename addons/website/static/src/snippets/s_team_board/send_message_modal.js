import { Component, useProps, t, signal }  from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";

export class SendMessageModal extends Component {
    static template = "website.s_team_board.send_message_modal"
    static components = { Dialog }

    props = useProps({
        name: t.string(),
        role: t.string(),
        description: t.string(),
        photo: t.string(),
    });

    isLoading = signal(false)

    setup() {
        this.notification = useService("notification");
    }

    async onSendMessage() {
        if (this.isLoading()) return;

        this.isLoading.set(true);
        try {
            await this.fakeApiCall();
            this.notification.add("Your message has been sent", {
                title: "Success",
                type: "success",
                sticky: false,
            });
            this.env.dialogData.close();
        } catch (error) {
            this.notification.add("Could not send your message", {
                title: "Error",
                type: "danger",
                sticky: true,
            });
        } finally {
            this.isLoading.set(false);
        }
    }

    async fakeApiCall(failureProbability = 0.5) {
        return new Promise((resolve, reject) => {
            setTimeout(() => {
                const shouldFail = Math.random() < failureProbability;

                if (shouldFail) {
                    reject(new Error("Random error"));
                } else {
                    resolve({ success: true, data: "Random success" });
                }
            }, 2000);
        });
    }
}
