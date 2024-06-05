/** @odoo-module **/

import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";
import publicWidget from "@web/legacy/js/public/public_widget";
import { formatCurrency, getCurrency } from "@web/core/currency";
import { formatDate, parseDate } from "@web/core/l10n/dates";

// Widget responsible for opening the modal
publicWidget.registry.PortalLoyaltyWidget = publicWidget.Widget.extend({
    selector: ".o_modal_test_selector",
    events: {
        "click .o_modal_test_event_click": "_onPortalLoyalty",
    },

    _onPortalLoyalty(ev) {
        const title = ev.currentTarget.dataset.title;
        const points = ev.currentTarget.dataset.points;
        const pointName = ev.currentTarget.dataset.pointName;
        const couponId = parseInt(ev.currentTarget.dataset?.couponId);
        const programId = parseInt(ev.currentTarget.dataset?.programId);
        // const value = ev.currentTarget.dataset.value;
        const type = ev.currentTarget.dataset.type;
        const topUpValues = ev.currentTarget.dataset.topUpValues?.match(/(\d+(?:\.\d+)?)/g).map(
            value => parseFloat(value)
        );
        // TODO: MATP check the mandatory value and their formats :/
        // if (!rewardId || !title) {
        //     return;
        // }
        // Open the modal
        this.call("dialog", "add", PortalLoyalty, {
            title: title,
            couponId: couponId,
            programId: programId,
            points: points,
            pointName: pointName,
            type: type,
            topUpValues: topUpValues,
        });
    },
});

import { Dialog } from "@web/core/dialog/dialog";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import {
    Component,
    useState,
    onWillStart,
} from "@odoo/owl";

// class CustomDialog extends Dialog {
//     static props = {
//         ...Dialog.props,
//         points: { type: String },
//         pointName: { type: String },
//         type: { type: String },
//     };
// }

export class PortalLoyalty extends Component {
    static components = {
        Dialog,
        Dropdown,
        DropdownItem,
    };
    static template = 'portal_loyalty_modal.LoyaltyModal';
    static props = {
        close: { type: Function, optional: true },
        title: { type: String, optional: true },
        couponId: { type: Number, optional: true },
        programId: { type: Number, optional: true },
        points: { type: String },
        pointName: { type: String },
        type: { type: String },
        topUpValues: { type: Array, optional: true },
    };

    setup() {
        this.title = this.props.title;
        this.points = this.props.points;
        this.pointName = this.props.pointName;
        this.topUpValues = this.props.topUpValues;
        this.is_ewallet = this.props.type == 'ewallet';
        this.is_loyalty = this.props.type == 'loyalty'

        this.state = useState({
            currencyId: null,
            history: [],
            topUpIndex: 0,
        });

        onWillStart(this.onWillStartHandler.bind(this));
    }

    async onWillStartHandler() {
        const { currencyId, history, rewards } = await rpc("/my/rewards/history", {
            coupon_id: this.props.couponId,
            program_id: this.props.programId,
        });
        this.state.history = history;
        this.state.currencyId = currencyId;
        this.state.rewards = rewards;
    }

    formatDate(date) {
        return formatDate(parseDate(date));
    }

    formatPoints(points){
        if (this.pointName == getCurrency(this.state.currencyId).symbol)
            return formatCurrency(points, this.state.currencyId);
        if (points % 1 === 0)
            return points.toString() + " " + this.pointName;
        return points.toFixed(2) + " " + this.pointName;
    }

    async topUpNow() {
        console.log("Top-Up for", this.topUpValues[this.state.topUpIndex], this.props.pointName);
    }
}
