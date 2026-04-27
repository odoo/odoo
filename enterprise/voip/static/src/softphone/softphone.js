import { Component, useEffect, useRef, useState } from "@odoo/owl";

import { ActivitiesTab } from "@voip/softphone/activities_tab";
import { CallInvitation } from "@voip/softphone/call_invitation";
import { ContactsTab } from "@voip/softphone/contacts_tab";
import { CorrespondenceDetails } from "@voip/softphone/correspondence_details";
import { Numpad } from "@voip/softphone/numpad";
import { RecentTab } from "@voip/softphone/recent_tab";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { isEventHandled, markEventHandled } from "@web/core/utils/misc";
import { useDebounced } from "@web/core/utils/timing";

export class Softphone extends Component {
    static components = {
        ActivitiesTab,
        CallInvitation,
        ContactsTab,
        CorrespondenceDetails,
        Numpad,
        RecentTab,
    };
    static props = {};
    static template = "voip.Softphone";

    setup() {
        this.store = useState(useService("mail.store"));
        this.voip = useState(useService("voip"));
        this.callService = useService("voip.call");
        this.userAgent = useService("voip.user_agent");
        this.searchBar = useRef("search");
        this.softphone = useState(this.voip.softphone);
        useEffect(
            (shouldFocus) => {
                if (shouldFocus && this.searchBar.el && !this.voip.error) {
                    this.searchBar.el.focus();
                    this.voip.softphone.shouldFocus = false;
                }
            },
            () => [this.voip.softphone.shouldFocus]
        );
        this.onInputSearchBar = useDebounced(() => this.search(), 300);
    }

    /** @returns {string} */
    get activeTabId() {
        return this.softphone.activeTabId;
    }

    /** @returns {string} */
    get callButtonTitleText() {
        if (!this.softphone.selectedCorrespondence?.call?.isInProgress) {
            return _t("Call");
        }
        return _t("End Call");
    }

    get firstItem() {
        // FIXME: items should be correspondences
        switch (this.activeTabId) {
            case "contacts":
                return Object.values(this.store.Persona.records).find((p) => p.hasPhoneNumber);
            case "activity":
                return this.softphone.activities[0];
            case "recent":
                return this.softphone.recentCalls[0];
            default:
                throw Error("Cannot get first item of current tab: unknown tab id.");
        }
    }

    get icon() {
        if (this.voip.hasPendingRequest) {
            return "fa fa-spin fa-circle-o-notch";
        }
        return "oi oi-voip";
    }

    /** @returns {boolean} */
    get isFolded() {
        return this.softphone.isFolded;
    }

    /** @returns {boolean} */
    get isOnSmallDevice() {
        return this.env.services.ui.isSmall;
    }

    /** @returns {boolean} */
    get isUiBlocked() {
        if (this.voip.error) {
            return !this.voip.error.isNonBlocking;
        }
        return false;
    }

    /** @returns {string} */
    get numpadButtonTitleText() {
        return this.softphone.numpad.isOpen ? _t("Close Numpad") : _t("Open Numpad");
    }

    /** @returns {boolean} */
    get shouldDisplayCallInvitation() {
        const call = this.softphone.selectedCorrespondence?.call;
        if (!call) {
            return false;
        }
        return (
            call.state === "calling" &&
            call.direction === "incoming" &&
            Boolean(this.userAgent.session)
        );
    }

    /** @returns {boolean} */
    get shouldDisplayCorrespondenceDetails() {
        return Boolean(this.softphone.selectedCorrespondence);
    }

    get tabList() {
        return [
            { id: "recent", name: _t("Recent") },
            { id: "activity", name: _t("Next Activities") },
            { id: "contacts", name: _t("Contacts") },
        ];
    }

    /** @returns {string} */
    get topbarText() {
        switch (this.voip.missedCalls) {
            case 0:
                return _t("VoIP");
            case 1:
                return _t("1 missed call");
            case 2:
                return _t("2 missed calls");
            default:
                return _t("%(number)s missed calls", { number: this.voip.missedCalls });
        }
    }

    /** @param {MouseEvent} ev */
    onClickClose(ev) {
        markEventHandled(ev, "Softphone.close");
        this.softphone.hide();
    }

    /** @param {MouseEvent} ev */
    onClickError(ev) {
        if (this.isUiBlocked) {
            return;
        }
        this.voip.resolveError();
    }

    /** @param {MouseEvent} ev */
    onClickNumpad(ev) {
        if (this.softphone.numpad.isOpen) {
            this.softphone.closeNumpad();
            this.softphone.shouldFocus = true;
        } else {
            this.softphone.openNumpad();
        }
    }

    /** @param {MouseEvent} ev */
    onClickPhone(ev) {
        if (this.softphone.selectedCorrespondence?.call?.isInProgress) {
            this.userAgent.hangup();
            return;
        }
        /**
         * The auto-call mode should be turned on when clicking on the call
         * button from the “Next Activities” tab without anything selected.
         */
        if (
            this.activeTabId === "activity" &&
            !this.softphone.numpad.isOpen &&
            !this.softphone.selectedCorrespondence &&
            this.firstItem
        ) {
            this.softphone.selectCorrespondence({ activity: this.firstItem });
            this.softphone.isInAutoCallMode = true;
            return;
        }
        const callData = this._getCallData();
        if (!callData) {
            return;
        }
        this.userAgent.makeCall(callData);
    }

    /** @param {MouseEvent} ev */
    onClickPostpone(ev) {
        this.softphone.selectedCorrespondence.call.activity.postponed = true;
        this.userAgent.hangup({ activityDone: false });
    }

    /** @param {MouseEvent} ev */
    onClickTab(ev) {
        this.softphone.activeTabId = ev.target.dataset.tabId;
    }

    /** @param {MouseEvent} ev */
    onClickTopbar(ev) {
        if (isEventHandled(ev, "Softphone.close") || this.isOnSmallDevice) {
            return;
        }
        if (this.isFolded) {
            this.softphone.unfold();
            this.voip.resetMissedCalls();
        } else {
            this.softphone.fold();
        }
    }

    search() {
        switch (this.activeTabId) {
            case "contacts":
                this.voip.fetchContacts(this.softphone.searchBarInputValue.trim());
                break;
            case "activity":
                this.voip.fetchTodayCallActivities();
                break;
            case "recent":
                this.voip.fetchRecentCalls();
                break;
        }
    }

    _getCallData() {
        if (this.softphone.numpad.isOpen) {
            const phoneNumber = this.softphone.numpad.value;
            if (phoneNumber === "") {
                return null;
            }
            return { phone_number: phoneNumber };
        }
        if (this.softphone.selectedCorrespondence) {
            const { activity, partner, phoneNumber } = this.softphone.selectedCorrespondence;
            return { activity, partner, phone_number: phoneNumber };
        }
        if (this.firstItem) {
            // Note: would be simpler if all tab items were of the same type (e.g. correspondences)
            let partner, phoneNumber;
            switch (this.activeTabId) {
                case "contacts":
                    partner = this.firstItem;
                    phoneNumber = this.firstItem.mobileNumber || this.firstItem.landlineNumber;
                    break;
                case "recent":
                    partner = this.firstItem.partner;
                    phoneNumber = this.firstItem.phoneNumber;
                    break;
                default:
                    return null;
            }
            return { partner, phone_number: phoneNumber };
        }
        return null;
    }
}
