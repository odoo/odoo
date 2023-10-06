/** @odoo-module **/
import { _t } from "@web/core/l10n/translation";

import { registry } from "@web/core/registry";
import { ShareBar } from "@marketing_card/card_campaign/card_campaign_share_button";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

import { renderToMarkup } from "@web/core/utils/render";
import { useService } from "@web/core/utils/hooks";
import { Component, markup, useState, useEffect } from "@odoo/owl";

class CardCampaign extends Component {
    static components = {
        ShareBar,
    };
    static props = {
        campaignId: { type: Number },
        linkSharedThanksMessage: { type: String, optional: true },
        linkSharedRewardUrl: { type: String, optional: true },
        postText: { type: String, optional: true },
        shareUrl: { type: String },
        hashToken: { type: String },
    };
    static template = "marketing_card.CardCampaign";

    setup() {
        this.dialog = useService("dialog");
        this.state = useState({
            message: this.props.linkSharedThanksMessage
                ? markup(this.props.linkSharedThanksMessage)
                : "",
            rewardUrl: this.props.linkSharedRewardUrl,
        });
        this.busService = this.env.services.bus_service;
        if (this.props.hashToken) {
            this.busService.addChannel(
                `card_shared_target-${this.props.campaignId}-${this.props.hashToken}`,
            );
            this.busService.subscribe(
                "marketing_card/share_card_target",
                ({ message, reward_url }) => {
                    this.state.message = message ? markup(message) : "";
                    this.state.rewardUrl = reward_url;
                },
            );
        }
        useEffect(
            () => {
                if (this.state.message || this.state.rewardUrl) {
                    this.dialog.add(ConfirmationDialog, {
                        title: _t("Thank You!"),
                        body: renderToMarkup("marketing_card.ThanksMessage", {
                            message: markup(`<div>${this.state.message}</div>`), // avoids text-prewrap style
                            rewardUrl: this.state.rewardUrl,
                        }),
                        confirmLabel: _t("Close"),
                    });
                }
            },
            () => [this.state.message || this.state.rewardUrl],
        );
    }
}

registry.category("public_components").add("card_campaign", CardCampaign);
