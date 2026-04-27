import { Component, useExternalListener, useState } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

/**
 * Represents a button in CRM leads Kanban view cards that deletes or creates
 * call activity from the related record. Call activities created this way are
 * included in the "Next activities" tab of the softphone.
 *
 * The term "call queue" refers to the list of the elements in the "Next
 * activities" tab.
 */
export class CallQueueSwitch extends Component {
    static props = standardFieldProps;
    static template = "voip.CallQueueSwitch";

    /**
     * Useful to prevent other unnecessary requests to the ORM being sent if one
     * is already in progress.
     */
    _hasPendingRequest = false;

    setup() {
        this.state = useState({ isRecordInCallQueue: this.props.record.data[this.props.name] });
        this.orm = useService("orm");
        this.voip = useService("voip");
        // useful to update the state of this view when the record is deleted
        // from the "Next Activities" tab of the softphone
        useExternalListener(this.voip.bus, "on-call-activity-removed", this._onCallActivityRemoved);
    }

    /** @returns {string} */
    get iconClasses() {
        return this.state.isRecordInCallQueue ? "fa-minus text-danger" : "fa-plus text-success";
    }

    /** @returns {string} */
    get titleText() {
        return this.state.isRecordInCallQueue
            ? _t("Remove from Call Queue")
            : _t("Add to Call Queue");
    }

    async addToCallQueue() {
        if (this._hasPendingRequest) {
            return;
        }
        await this._makeRequest(() =>
            this.orm.call(this.props.record.resModel, "create_call_activity", [
                [this.props.record.resId],
            ])
        );
        this.state.isRecordInCallQueue = true;
        await this.props.record.load();
        this.props.record.model.notify();
    }

    /** @param {MouseEvent} ev */
    onClick(ev) {
        if (this.state.isRecordInCallQueue) {
            this.removeFromCallQueue();
        } else {
            this.addToCallQueue();
        }
    }

    async removeFromCallQueue() {
        if (this._hasPendingRequest) {
            return;
        }
        await this._makeRequest(async () =>
            this.orm.call(this.props.record.resModel, "delete_call_activity", [
                [this.props.record.resId],
            ])
        );
        this.state.isRecordInCallQueue = false;
        await this.props.record.load();
        this.props.record.model.notify();
    }

    /** @param {function} callback */
    async _makeRequest(callback) {
        this._hasPendingRequest = true;
        await callback();
        this._hasPendingRequest = false;
    }

    /**
     * @param {Object} param0
     * @param {integer} param0.detail The resId of the deleted record.
     */
    _onCallActivityRemoved({ detail: resId }) {
        // note: the resId is enough to identify the record as long as only
        // crm.lead uses the CallQueueSwitch field widget.
        if (this.props.record.resId !== resId) {
            return;
        }
        this.state.isRecordInCallQueue = false;
    }
}

registry.category("fields").add("call_queue_switch", { component: CallQueueSwitch });
