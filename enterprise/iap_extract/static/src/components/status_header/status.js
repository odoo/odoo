/** @odoo-module **/

import { Component, onWillDestroy, onWillStart, onWillUpdateProps, useState } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

const CHECK_OCR_WAIT_DELAY = 5*1000;

export class StatusHeader extends Component {
    static template = "account_invoice_extract.Status";
    static props = standardFieldProps;

    setup() {
        this.state = useState({
            status: this.props.record.data.extract_state,
            errorMessage: this.props.record.data.extract_error_message,
            retryLoading: false,
            checkStatusLoading: false,
        });
        this.orm = useService("orm");
        this.action = useService("action");
        this.busService = this.env.services.bus_service;

        onWillStart(() => {
            // When a new document is uploaded (via the Upload button, or by attaching a file),
            // the server will send a `extract_mixin_new_document` message on the bus with the
            // `extract_document_uuid` created upon submitting the document to the OCR server.
            // We can then subscribe for state changes event of this document uuid
            // (typically when OCR has finished processing it)
            this.busService.subscribe("extract_mixin_new_document", (params) => {
                this.state.status = params.status;
                this.state.errorMessage = params.error_message;
                this.subscribeToChannel(params.extract_document_uuid);
            });
            this.busService.subscribe("state_change", ({status, error_message})=> {
                this.state.status = status;
                this.state.errorMessage = error_message;
            });
            this.enableTimeout();
        });

        onWillDestroy(() => {
            this.busService.deleteChannel(this.channelName);
            this.state.status = 'no_extract_requested';
            clearTimeout(this.timeoutId);
        });

        onWillUpdateProps((nextProps) => {
            if (nextProps.record.id !== this.props.record.id) {
                this.state.errorMessage = nextProps.record.data.extract_error_message;
                this.state.status = nextProps.record.data.extract_state;
                this.subscribeToChannel(nextProps.record.data.extract_document_uuid);
                this.enableTimeout();
            }
        });
    }

    subscribeToChannel(documentUUID) {
        if (!documentUUID) {
            return;
        }
        this.busService.deleteChannel(this.channelName);
        this.channelName = `extract.mixin.status#${documentUUID}`;
        this.busService.addChannel(this.channelName);
    }

    enableTimeout () {
        if (!['waiting_extraction', 'extract_not_ready'].includes(this.state.status)) {
            return;
        }

        clearTimeout(this.timeoutId);

        this.timeoutId = setTimeout(async () => {
            if (['waiting_extraction', 'extract_not_ready'].includes(this.state.status)) {
                const [status, errorMessage] = (await this.orm.call(
                    this.props.record.resModel,
                    "check_ocr_status",
                    [this.props.record.resId],
                    {}
                ))[0];
                this.state.status = status;
                this.state.errorMessage = errorMessage;
            }
        }, CHECK_OCR_WAIT_DELAY);
    }

    async checkOcrStatus() {
        this.state.checkStatusLoading = true;
        const [status, errorMessage] = (await this.orm.call(
            this.props.record.resModel,
            "check_ocr_status",
            [this.props.record.resId],
            {}
        ))[0];
        if (status === "waiting_validation") {
            await this.refreshPage();
            return;
        }
        this.state.status = status;
        this.state.errorMessage = errorMessage;
        this.state.checkStatusLoading = false;
    }

    async refreshPage() {
        await this.action.switchView("form", {
            resId: this.props.record.resId,
            resIds: this.props.record.resIds
        });
    }

    async buyCredits() {
        const actionData = await this.orm.call(this.props.record.resModel, "buy_credits", [this.props.record.resId], {});
        this.action.doAction(actionData);
    }

    async retryDigitalization() {
        this.state.retryLoading = true;
        const [status, errorMessage, documentUUID] = await this.orm.call(this.props.record.resModel, "action_manual_send_for_digitization", [this.props.record.resId], {});
        this.subscribeToChannel(documentUUID);
        this.state.status = status;
        this.state.errorMessage = errorMessage;
        this.state.retryLoading = false;
        this.enableTimeout();
    }
}

registry.category("fields").add("extract_state_header", {component: StatusHeader});
