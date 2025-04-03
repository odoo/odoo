import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";
import { renderToFragment, renderToMarkup } from "@web/core/utils/render";

export class MailingPortalSubscription extends Interaction {
    static selector = "#o_mailing_portal_subscription";

    dynamicContent = {
        // Subscriptions & blocklist info textbox
        "#o_mailing_subscription_update_info": {
            "t-att-class": () => ({
                "d-none": this.subscriptionStatus == "idle",
                "text-success": [
                    "blocklist_add",
                    "blocklist_remove",
                    "subscription_updated",
                ].includes(this.subscriptionStatus),
                "text-danger": this.subscriptionStatus == "error",
            }),
            "t-out": () => this._subscriptionUpdateInfo(),
        },

        // Blocklist controls
        "#button_blocklist_add": {
            "t-att-class": () => ({
                "d-none": !(
                    this.customerData.blocklistEnabled &&
                    this.customerData.blocklistPossible &&
                    !this.customerData.isBlocklisted
                ),
            }),
            "t-on-click": (ev) => this._onBlocklistAddClick(ev),
        },
        "#button_blocklist_remove": {
            "t-att-class": () => ({ "d-none": !this.customerData.isBlocklisted }),
            "t-on-click": (ev) => this._onBlocklistRemoveClick(ev),
        },

        // "Is Blocklisted" message
        "#o_mailing_subscription_form_blocklisted": {
            "t-att-class": () => ({
                "d-none": !this.customerData.isBlocklisted,
            }),
        },

        // Subscription form
        "#o_mailing_subscription_form_manage": {
            "t-att-class": () => ({
                "d-none": this.customerData.isBlocklisted,
            }),
        },
        "#o_mailing_subscription_form_manage input": {
            "t-att-disabled": () => (this.customerData.isBlocklisted ? "disabled" : false),
        },
        ".mailing_lists_checkboxes": {
            "t-att-disabled": () => (this.customerData.isBlocklisted ? "disabled" : false),
            "t-att-class": () => ({
                "d-none": this.customerData.isBlocklisted,
            }),
        },
        "#button_subscription_update_preferences": {
            "t-att-class": () => ({
                "d-none": this.customerData.isBlocklisted,
            }),
            "t-on-click": (ev) => this._onSubscriptionUpdate(ev),
        },

        // Feedback form title
        "div#o_mailing_subscription_feedback p": {
            "t-out": () =>
                this.lastAction == "blocklist_add"
                    ? _t("Please let us know why you want to be in our block list.")
                    : _t("Please let us know why you updated your subscription."),
        },

        // Feedback form
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
        ".o_mailing_subscription_opt_out_reason": {
            "t-on-click": (ev) =>
                this._onSelectOptOutReason(ev),
        },
        "#o_mailing_subscription_feedback": {
            "t-att-class": () => ({
                "d-none": !this.customerData.feedbackEnabled,
            }),
        },
        "#o_mailing_subscription_feedback_textarea": {
            "t-att-class": () => ({ "d-none": !this.displayFeedbackTextArea }),
        },
        "#button_feedback": {
            "t-att-disabled": () => !this.enableFeedbackButton,
            "t-on-click": (ev) => this._onFeedbackSendClick(ev),
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
        this._resetFeedbackForm();

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

    _subscriptionUpdateInfo() {
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
    async _onFeedbackSendClick(event) {
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
                    this._resetFeedbackForm();
                }
                this.feedbackStatus = result === true ? "feedback_sent" : "error";
                this.lastAction = result === true ? "feedback_sent" : result;
            })
        );
    }

    _onSelectOptOutReason(ev) {
        this.enableFeedbackButton = true;
        // Show feedback text area if option is set to "Other"
        if (ev.target.value === "5") {
            this.displayFeedbackTextArea = true;
        } else {
            this.displayFeedbackTextArea = false;
        }
    }

    _resetFeedbackForm() {
        document.querySelectorAll(".o_mailing_subscription_opt_out_reason").forEach((el) => {
            el.checked = false;
        })
        document.getElementById("o_mailing_subscription_feedback_textarea").value = "";
        this.enableFeedbackButton = false;
        this.feedbackStatus = "idle";
        this.displayFeedbackTextArea = false;
    }

    /****************************************************
     ***************** Subscription Form ****************
     ****************************************************/

    /*
     * Triggers call to update list subscriptions. Bubble up to let parent
     * handle returned result if necessary. RPC call returns number of optouted
     * lists, used by parent widget notably to know which feedback to ask.
     */
    async _onSubscriptionUpdate(event) {
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
                const has_error = ["error", "unauthorized"].includes(result);
                if (!has_error) {
                    this.subscriptionStatus = "subscription_updated";
                    this._updateDisplayForm(mailingListOptinIds);
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
    _updateDisplayForm(listOptinIds) {
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

    /****************************************************
     **************** Blocklist Buttons *****************
     ****************************************************/

    /*
     * Triggers call to add current email in blocklist. Update internals accordingly
     */
    async _onBlocklistAddClick(event) {
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
     * Triggers call to remove current email from blocklist. Update internals accordingly
     */
    async _onBlocklistRemoveClick(event) {
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
                    this._resetFeedbackForm();
                }
                this.subscriptionStatus = result === true ? "blocklist_remove" : "error";
                this.lastAction = result === true ? "blocklist_remove" : result;
            })
        );
    }
}

registry
    .category("public.interactions")
    .add("mass_mailing.mailing_portal_subscription_int", MailingPortalSubscription);
