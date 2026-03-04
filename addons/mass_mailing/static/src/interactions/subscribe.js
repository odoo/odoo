import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { renderToMarkup, renderToFragment } from "@web/core/utils/render";
import { _t } from "@web/core/l10n/translation";

export class Subscribe extends Interaction {
    static selector = "#o_mailing_portal_subscription";
    dynamicContent = {
        // Subscription form
        "#o_mailing_subscription_form #o_mailing_subscription_form_manage": {
            "t-att-class": () => ({
                "d-none": this.customerData.isBlocklisted,
            }),
        },
        "#o_mailing_subscription_form #o_mailing_subscription_form_manage input": {
            "t-att-disabled": () => this.customerData.isBlocklisted,
        },
        "#o_mailing_subscription_form #button_form_send": {
            "t-on-click.prevent": this.onSubscriptionUpdate,
            "t-att-class": () => ({
                "d-none": this.customerData.isBlocklisted,
            }),
            "t-att-disabled": () => this.customerData.isBlocklisted,
        },
        "#o_mailing_subscription_form .mailing_lists_checkboxes": {
            "t-att-disabled": () => (this.customerData.isBlocklisted ? "disabled" : false),
            "t-att-class": () => ({
                "d-none": this.customerData.isBlocklisted,
            }),
        },
        "#button_subscription_update_preferences": {
            "t-att-class": () => ({
                "d-none": this.customerData.isBlocklisted,
            }),
            "t-on-click": this.onSubscriptionUpdate,
        },

        // Subscriptions & blocklist info textbox
        "#o_mailing_subscription_form #o_mailing_subscription_update_info": {
            "t-att-class": () => ({
                "d-none": this.subscriptionStatus == "idle",
                "text-success": [
                    "blocklist_add",
                    "blocklist_remove",
                    "subscription_updated",
                ].includes(this.subscriptionStatus),
                "text-danger": this.subscriptionStatus == "error",
            }),
            "t-out": () => this.subscriptionUpdateInfo(),
        },

        // Blocklist controls
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
            "t-on-click": this.onBlocklistRemoveClick,
            "t-att-class": () => ({
                "d-none": !this.customerData.isBlocklisted,
            }),
        },

        // "Is Blocklisted" message
        "#o_mailing_subscription_form #o_mailing_subscription_form_blocklisted": {
            "t-att-class": () => ({
                "d-none": !this.customerData.isBlocklisted,
            }),
        },

        // Feedback form title
        "#o_mailing_subscription_feedback": {
            "t-att-class": () => ({
                "d-none": !this.customerData.feedbackEnabled,
            }),
        },
        "#o_mailing_subscription_feedback p": {
            "t-out": () =>
                this.lastAction == "blocklist_add"
                    ? _t("Please let us know why you want to be in our block list.")
                    : _t("Please let us know why you updated your subscription."),
        },

        // Feedback form
        "#o_mailing_subscription_feedback input": {
            "t-att-disabled": () => this.unsubscribeFeedbackStatus === "feedback_sent",
        },
        "#o_mailing_subscription_feedback .o_mailing_subscription_opt_out_reason": {
            "t-on-click": this.onOptOutReasonClick,
        },
        "#o_mailing_subscription_feedback_textarea": {
            "t-att-class": () => ({ "d-none": !this.displayFeedbackTextArea }),
        },
        "#o_mailing_subscription_feedback #button_feedback": {
            "t-on-click.prevent": this.onFeedbackSendClick,
            "t-att-disabled": () => !this.enableFeedbackButton,
        },
        "#o_mailing_subscription_feedback_info": {
            "t-att-class": () => ({
                "d-none": this.feedbackStatus == "idle",
                "text-success": this.feedbackStatus == "feedback_sent",
                "text-danger": this.feedbackStatus == "error",
            }),
            "t-out": () =>
                renderToMarkup("mass_mailing.portal.feedback_update_info", {
                    infoKey: this.feedbackStatus,
                }),
        },
    };

    setup() {
        super.setup();

        // startup info
        this.subscriptionStatus = "idle";
        this.customerData = { ...document.getElementById("o_mailing_portal_subscription").dataset };
        this.customerData.documentId = parseInt(this.customerData.documentId || 0);
        this.customerData.mailingId = parseInt(this.customerData.mailingId || 0);
        this.lastAction = this.customerData.lastAction;
        this.resetFeedbackForm();

        // subscription form
        this.listInfo = [
            ...document.querySelectorAll("#o_mailing_subscription_form_manage input"),
        ].map((node) => {
            const listInfo = {
                description: node.dataset.description || "",
                id: parseInt(node.getAttribute("value")),
                member: node.dataset.member === "1",
                name: node.getAttribute("title"),
                opt_out: node.getAttribute("checked") !== "checked",
            };
            return listInfo;
        });
    }

    /****************************************************
     **************** Blocklist Buttons *****************
     ****************************************************/

    /*
     * Triggers call to add current email in blocklist. Update widget internals
     * and DOM accordingly (buttons display mainly).
     */
    async onBlocklistAddClick(event) {
        event.preventDefault();
        return await this.waitFor(
            rpc("/mailing/blocklist/add", {
                document_id: this.customerData.documentId,
                email: this.customerData.email,
                hash_token: this.customerData.hashToken,
                mailing_id: this.customerData.mailingId,
            }).then((result) => {
                if (result === true) {
                    this.customerData.isBlocklisted = true;
                    this.customerData.feedbackEnabled = true;
                }
                this.subscriptionStatus = result === true ? "blocklist_add" : "error";
                this.lastAction = result === true ? "blocklist_add" : result;
            })
        );
    }

    /*
     * Triggers call to remove current email from blocklist. Update widget
     * internals and DOM accordingly (buttons display mainly).
     */
    async onBlocklistRemoveClick(event) {
        event.preventDefault();
        return await this.waitFor(
            rpc("/mailing/blocklist/remove", {
                document_id: this.customerData.documentId,
                email: this.customerData.email,
                hash_token: this.customerData.hashToken,
                mailing_id: this.customerData.mailingId,
            }).then((result) => {
                if (result === true) {
                    this.customerData.isBlocklisted = false;
                    this.customerData.feedbackEnabled = false;
                    this.resetFeedbackForm();
                }
                this.subscriptionStatus = result === true ? "blocklist_remove" : "error";
                this.lastAction = result === true ? "blocklist_remove" : result;
            })
        );
    }

    /****************************************************
     ***************** Subscription Form ****************
     ****************************************************/

    /*
     * Triggers call to update list subscriptions. Bubble up to let parent
     * handle returned result if necessary. RPC call returns number of optouted
     * lists, used by parent widget notably to know which feedback to ask.
     */
    async onSubscriptionUpdate(event) {
        event.preventDefault();
        const formData = new FormData(
            document.querySelector("div#o_mailing_subscription_form form")
        );
        const mailingListOptinIds = formData
            .getAll("mailing_list_ids")
            .map((id_str) => parseInt(id_str));
        return await this.waitFor(
            rpc("/mailing/list/update", {
                csrf_token: formData.get("csrf_token"),
                document_id: this.customerData.documentId,
                email: this.customerData.email,
                hash_token: this.customerData.hashToken,
                lists_optin_ids: mailingListOptinIds,
                mailing_id: this.customerData.mailingId,
            }).then((result) => {
                this.customerData.feedbackEnabled = false;
                const has_error = ["error", "unauthorized"].includes(result);
                if (!has_error) {
                    this.subscriptionStatus = "subscription_updated";
                    this.updateDisplayForm(mailingListOptinIds);
                } else {
                    this.subscriptionStatus = "error";
                }
            })
        );
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
            email: this.customerData.email,
            listsMemberOrPoposal: this.listInfo,
        });
        const manageForm = document.getElementById("o_mailing_subscription_form_manage");
        manageForm.replaceChildren(formContent);
        // Handle line breaks on re-rendering text descriptions
        const listDescriptions = document.querySelectorAll(
            ".o_mailing_subscription_form_list_description"
        );
        listDescriptions.forEach((listDescription) => {
            listDescription.innerHTML = listDescription.dataset.description.replaceAll("\n", "<br>");
        });
    }

    subscriptionUpdateInfo() {
        switch (this.subscriptionStatus) {
            case "blocklist_add":
            case "blocklist_remove":
                return renderToMarkup("mass_mailing.portal.blocklist_update_info", {
                    infoKey: this.subscriptionStatus,
                });
            case "subscription_updated":
            case "error":
                return renderToMarkup("mass_mailing.portal.list_form_update_status", {
                    infoKey: this.subscriptionStatus,
                });
            default:
                return "";
        }
    }

    /****************************************************
     ****************** Feedback Form *******************
     ****************************************************/

    /*
     * Triggers call to give a feedback about current subscription update.
     */
    async onFeedbackSendClick(event) {
        event.preventDefault();
        const formData = new FormData(
            document.querySelector("div#o_mailing_subscription_feedback form")
        );
        const optoutReasonId = parseInt(formData.get("opt_out_reason_id"));
        return await this.waitFor(
            rpc("/mailing/feedback", {
                csrf_token: formData.get("csrf_token"),
                document_id: this.customerData.documentId,
                email: this.customerData.email,
                feedback: formData.get("feedback"),
                hash_token: this.customerData.hashToken,
                last_action: this.lastAction,
                mailing_id: this.customerData.mailingId,
                opt_out_reason_id: optoutReasonId,
            }).then((result) => {
                if (result === true) {
                    this.customerData.feedbackEnabled = false;
                    this.resetFeedbackForm();
                }
                this.feedbackStatus = result === true ? "feedback_sent" : "error";
                this.lastAction = result === true ? "feedback_sent" : result;
            })
        );
    }

    /*
     * Toggle feedback textarea display based on reason configuration
     */
    onOptOutReasonClick(ev) {
        this.enableFeedbackButton = true;
        // Show feedback text area if option is set to "Other"
        if (ev.target.value === "5") {
            this.displayFeedbackTextArea = true;
        } else {
            this.displayFeedbackTextArea = false;
        }
    }

    resetFeedbackForm() {
        document.querySelectorAll(".o_mailing_subscription_opt_out_reason").forEach((el) => {
            el.checked = false;
        });
        document.getElementById("o_mailing_subscription_feedback_textarea").value = "";
        this.enableFeedbackButton = false;
        this.feedbackStatus = "idle";
        this.displayFeedbackTextArea = false;
    }
}

registry.category("public.interactions").add("mass_mailing.subscribe", Subscribe);
