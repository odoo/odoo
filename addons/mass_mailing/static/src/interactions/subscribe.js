import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { renderToMarkup, renderToFragment } from "@web/core/utils/render";
import { _t } from "@web/core/l10n/translation";

export class Subscribe extends Interaction {
    static selector = "#o_mailing_portal_subscription";
    dynamicContent = {
        "#o_mailing_subscription_form #o_mailing_subscription_form_manage": {
            "t-att-class": () => ({
                "d-none": this.customerData.isBlocklisted,
            }),
        },
        "#o_mailing_subscription_form #o_mailing_subscription_form_manage input": {
            "t-att-disabled": () => this.customerData.isBlocklisted,
        },
        "#o_mailing_subscription_form #button_form_send": {
            "t-on-click.prevent": this.onFormSend,
            "t-att-class": () => ({
                "d-none": this.customerData.isBlocklisted,
            }),
            "t-att-disabled": () => this.customerData.isBlocklisted,
        },
        "#o_mailing_subscription_form #o_mailing_subscription_update_info": {
            "t-att-class": () => ({
                "d-none": this.changeSubscriptionStatus === "hidden",
                "text-success": !this.changeSubscriptionStatus.endsWith("error"),
                "text-danger": this.changeSubscriptionStatus.endsWith("error"),
            }),
            "t-out": () => this.changeSubscriptionResultMessage,
        },
        "#o_mailing_subscription_form #button_blocklist_add": {
            "t-on-click.prevent": this.onBlocklistAddClick,
            "t-att-class": () => ({
                "d-none":
                    !this.customerData.blocklistEnabled ||
                    !this.customerData.blocklistPossible ||
                    this.customerData.isBlocklisted,
            }),
        },
        "#o_mailing_subscription_form #button_blocklist_remove": {
            "t-on-click.prevent": this.onBlocklistRemoveClick,
            "t-att-class": () => ({
                "d-none": !this.customerData.isBlocklisted,
            }),
        },
        "#o_mailing_subscription_form #o_mailing_subscription_form_blocklisted": {
            "t-att-class": () => ({
                "d-none": !this.customerData.isBlocklisted,
            }),
        },
        "#o_mailing_subscription_feedback": {
            "t-att-class": () => ({
                "d-none": !this.customerData.feedbackEnabled,
            }),
        },
        "#o_mailing_subscription_feedback p": {
            "t-out": () =>
                this.askingFeedbackFor === "blocklist_add"
                    ? _t("Please let us know why you want to be in our block list.")
                    : _t("Please let us know why you updated your subscription."),
        },
        "#o_mailing_subscription_feedback input": {
            "t-att-disabled": () => this.unsubscribeFeedbackStatus === "feedback_sent",
        },
        "#o_mailing_subscription_feedback .o_mailing_subscription_opt_out_reason": {
            "t-on-click": this.onOptOutReasonClick,
        },
        "#o_mailing_subscription_feedback textarea": {
            "t-att-class": () => ({
                "d-none": !this.showFeedbackTextbox,
            }),
            "t-att-disabled": () => this.unsubscribeFeedbackStatus === "feedback_sent",
        },
        "#o_mailing_subscription_feedback #button_feedback": {
            "t-on-click.prevent": this.onFeedbackClick,
            "t-att-disabled": () => this.unsubscribeFeedbackStatus === "feedback_sent",
        },
        "#o_mailing_subscription_feedback #o_mailing_subscription_feedback_info": {
            "t-att-class": () => ({
                "d-none": this.unsubscribeFeedbackStatus === "hidden",
                "text-success": this.unsubscribeFeedbackStatus !== "error",
                "text-danger": this.unsubscribeFeedbackStatus === "error",
            }),
            "t-out": () => this.unsubscribeFeedbackResultMessage,
        },
    };

    setup() {
        this.customerData = { ...document.getElementById("o_mailing_portal_subscription").dataset };
        this.customerData.documentId = parseInt(this.customerData.documentId || 0);
        this.customerData.mailingId = parseInt(this.customerData.mailingId || 0);
        this.lastAction = this.customerData.lastAction;
        this.listInfo = this.getListInfo();
        this.showFeedbackTextbox = false;
        this.changeSubscriptionStatus = "hidden";
        this.unsubscribeFeedbackStatus = "hidden";
    }

    /*
     * Triggers call to add current email in blocklist. Update widget internals
     * and DOM accordingly (buttons display mainly).
     */
    async onBlocklistAddClick() {
        const result = await this.waitFor(
            rpc("/mailing/blocklist/add", {
                document_id: this.customerData.documentId,
                email: this.customerData.email,
                hash_token: this.customerData.hashToken,
                mailing_id: this.customerData.mailingId,
            })
        );
        this.protectSyncAfterAsync((result) => {
            if (result === true) {
                this.customerData.isBlocklisted = true;
                this.customerData.feedbackEnabled = true;
            }
            this.changeSubscriptionStatus = result === true ? "blocklist_add" : "blocklist_error";
            this.onActionDone(result === true ? "blocklist_add" : result);
        })(result);
    }

    /*
     * Triggers call to remove current email from blocklist. Update widget
     * internals and DOM accordingly (buttons display mainly).
     */
    async onBlocklistRemoveClick() {
        const result = await this.waitFor(
            rpc("/mailing/blocklist/remove", {
                document_id: this.customerData.documentId,
                email: this.customerData.email,
                hash_token: this.customerData.hashToken,
                mailing_id: this.customerData.mailingId,
            })
        );
        this.protectSyncAfterAsync((result) => {
            if (result === true) {
                this.customerData.isBlocklisted = false;
                this.customerData.feedbackEnabled = false;
            }
            this.changeSubscriptionStatus =
                result === true ? "blocklist_remove" : "blocklist_error";
            this.onActionDone(result === true ? "blocklist_remove" : result);
        })(result);
    }

    /*
     * Triggers call to update list subscriptions. RPC call returns number
     * of optouted lists, used to know which feedback to ask.
     */
    async onFormSend() {
        const formData = new FormData(
            document.querySelector("div#o_mailing_subscription_form form")
        );
        const mailingListOptinIds = formData
            .getAll("mailing_list_ids")
            .map((id_str) => parseInt(id_str));
        const result = await this.waitFor(
            rpc("/mailing/list/update", {
                csrf_token: formData.get("csrf_token"),
                document_id: this.customerData.documentId,
                email: this.customerData.email,
                hash_token: this.customerData.hashToken,
                lists_optin_ids: mailingListOptinIds,
                mailing_id: this.customerData.mailingId,
            })
        );
        this.protectSyncAfterAsync((result) => {
            const has_error = ["error", "unauthorized"].includes(result);
            let callKey;
            if (has_error) {
                callKey = "error";
            } else {
                callKey =
                    parseInt(result) > 0 ? "subscription_updated_optout" : "subscription_updated";
                this.updateDisplayForm(mailingListOptinIds);
            }
            this.changeSubscriptionStatus = has_error
                ? "subscription_error"
                : "subscription_updated";
            if (callKey === "subscription_updated_optout") {
                this.customerData.feedbackEnabled = true;
            } else if (callKey === "subscription_updated") {
                this.customerData.feedbackEnabled = false;
            }
            this.onActionDone(callKey);
        })(result);
    }

    /*
     * Triggers call to give a feedback about current subscription update.
     */
    async onFeedbackClick() {
        const formData = new FormData(
            document.querySelector("div#o_mailing_subscription_feedback form")
        );
        const optoutReasonId = parseInt(formData.get("opt_out_reason_id"));
        const result = await this.waitFor(
            rpc("/mailing/feedback", {
                csrf_token: formData.get("csrf_token"),
                document_id: this.customerData.documentId,
                email: this.customerData.email,
                feedback: formData.get("feedback"),
                hash_token: this.customerData.hashToken,
                last_action: this.lastAction,
                mailing_id: this.customerData.mailingId,
                opt_out_reason_id: optoutReasonId,
            })
        );
        this.protectSyncAfterAsync((result) => {
            if (result === true) {
                this.unsubscribeFeedbackStatus = "feedback_sent";
            } else {
                this.unsubscribeFeedbackStatus = "error";
            }
            this.lastAction = result === true ? "feedback_sent" : result;
        })(result);
    }

    /*
     * Toggle feedback textarea display based on reason configuration
     */
    onOptOutReasonClick(ev) {
        this.showFeedbackTextbox = ev.target.dataset["isFeedback"];
        document.querySelector("div#o_mailing_subscription_feedback textarea").value = "";
    }

    /**
     * Parse start values of mailing lists subscriptions based on generated DOM
     * from server. Done here to avoid having to generate it server-side and
     * propagating it through various layers.
     */
    getListInfo() {
        return [...document.querySelectorAll("#o_mailing_subscription_form_manage input")].map(
            (node) => {
                const listInfo = {
                    id: parseInt(node.getAttribute("value")),
                    member: node.dataset.member === "1",
                    name: node.getAttribute("title"),
                    opt_out: node.getAttribute("checked") !== "checked",
                };
                return listInfo;
            }
        );
    }

    onActionDone(callKey) {
        this.lastAction = callKey;
        if (["blocklist_add", "subscription_updated_optout"].includes(callKey)) {
            this.askingFeedbackFor = callKey;
        }
        this.unsubscribeFeedbackStatus = "hidden";
        document.querySelector("div#o_mailing_subscription_feedback textarea").value = "";
    }

    /*
     * Update display after subscription, notably to update mailing list subscription
     * status. We simply update opt_out status based on the ID being present in the
     * newly-selected opt-in mailing lists, then rerender the inputs.
     */
    updateDisplayForm(listOptinIds) {
        /* update internal status*/
        this.listInfo.forEach((listItem) => {
            listItem.member = listItem.member || listOptinIds.includes(listItem.id);
            listItem.opt_out = !listOptinIds.includes(listItem.id);
        });
        /* update form of lists for update */
        const formContent = renderToFragment("mass_mailing.portal.list_form_content", {
            listsMember: this.listInfo.filter((item) => item.member === true),
            listsProposal: this.listInfo.filter((item) => item.member === false),
        });
        const manageForm = document.getElementById("o_mailing_subscription_form_manage");
        manageForm.replaceChildren(formContent);
        /* update readonly display of customer's lists */
        const formReadonlyContent = renderToFragment(
            "mass_mailing.portal.list_form_content_readonly",
            {
                listsOptin: this.listInfo.filter((item) => item.opt_out === false),
            }
        );
        const readonlyForm = document.getElementById("o_mailing_subscription_form_blocklisted");
        readonlyForm.replaceChildren(formReadonlyContent);
    }

    /*
     * Retrieve the correct message to display based on the last action that the
     * user performed on the o_mailing_subscription_form element.
     * The possible situations are: added to blocklist, removed from blocklist,
     * error while changing blocklist status, updated subscriptions, and
     * error while updating subscription.
     */
    get changeSubscriptionResultMessage() {
        if (this.changeSubscriptionStatus == "hidden") {
            return null;
        }
        return renderToMarkup(
            this.changeSubscriptionStatus.startsWith("subscription")
                ? "mass_mailing.portal.list_form_update_info"
                : "mass_mailing.portal.blocklist_update_info",
            {
                infoKey: this.changeSubscriptionStatus,
            }
        );
    }

    /*
     * Retrieve the correct message to display based on the last action that the
     * user performed on the o_mailing_subscription_feedback element
     * (i.e., the questionnaire about the reason for unsubscribing).
     * The possible situations are feedback received and error.
     */
    get unsubscribeFeedbackResultMessage() {
        if (this.unsubscribeFeedbackStatus == "hidden") {
            return null;
        }
        return renderToMarkup("mass_mailing.portal.feedback_update_info", {
            infoKey: this.unsubscribeFeedbackStatus,
        });
    }
}

registry.category("public.interactions").add("mass_mailing.subscribe", Subscribe);
