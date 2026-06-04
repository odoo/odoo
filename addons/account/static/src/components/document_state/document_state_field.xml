<?xml version="1.0" encoding="utf-8"?>
<templates>
    <t t-name="account.DocumentStatePopover">
        <div class="row m-2 mt-4 justify-content-between account_document_state_popover">
            <span class="col-10" t-out="this.props.message" style="white-space: pre-wrap;"/>
            <button class="col-2 btn p-0 account_document_state_popover_clone" t-on-click="() => this.props.copyText()">
                <i class="oi" data-icon="assignment"/>
            </button>
        </div>
    </t>

    <t t-name="account.DocumentState" t-inherit="web.SelectionField" t-inherit-mode="primary">
        <span position="after">
            <span t-if="this.message"> </span>
            <a t-if="this.message"
               t-on-click="(ev) => this.showMessagePopover(ev)"
               class="oi" data-icon="info"/>
        </span>
    </t>
</templates>
