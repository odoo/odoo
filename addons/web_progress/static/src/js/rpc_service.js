/** @odoo-module **/

import {jsonrpc} from "@web/core/network/rpc_service";
import {registry} from "@web/core/registry";
import {BlockUI} from "@web/core/ui/block_ui";
import {download} from "@web/core/network/download";
import * as legacyEnv from "web.env";
import * as legacyProgressAjax from "web.progress.ajax";
import * as legacyProgressBar from "web.progress.bar";
import * as legacyProgressMenu from "web.progress.loading";

const {xml} = owl;

// -----------------------------------------------------------------------------
// download adapted to handle progress reporting
// -----------------------------------------------------------------------------

const org_download = download._download;

function _download(options) {
    // add progress_code to the context
    if (options.data) {
        var data = false;
        if (options.data.context) {
            // reports
            data = {'context': JSON.parse(options.data.context)};
            legacyProgressAjax.genericRelayEvents('/web/', 'call', data);
            options.data.context = JSON.stringify(data.context);
        } else if (options.data.data) {
            // export
            data = JSON.parse(options.data.data);
            legacyProgressAjax.genericRelayEvents('/web/', 'call', data);
            options.data.data = JSON.stringify(data);
        }
        if (data.context) {
            // block UI, because for unknown reason the UI is not blocked
            legacyProgressBar.blockUI();
            legacyProgressBar.addProgressBarToBlockedUI(data.context.progress_code);
        }
        return org_download(options).finally(() => {
            // in any case unblock UI
            legacyProgressBar.unblockUI();
        })
    }
}

download._download = _download;

// -----------------------------------------------------------------------------
// BlockUI adapted to handle progress reporting
// -----------------------------------------------------------------------------
function registerProgressBarBLockUI() {
    var BlockUIcomp = registry.category("main_components").get("BlockUI");

    if (BlockUIcomp && BlockUIcomp.props) {
        BlockUIcomp.props.bus.on("BLOCK", null, function() {
            legacyProgressBar.addProgressBarToBlockedUI(legacyProgressMenu.getProgressCode())
        });
        BlockUIcomp.props.bus.on("UNBLOCK", null, function() {legacyProgressBar.removeProgressBarFrmBlockedUI()});
    }

BlockUI.template = xml`
<div t-att-class="state.blockUI ? 'o_blockUI fixed-top d-flex justify-content-center align-items-center flex-column vh-100 bg-black-50' : ''">
  <t t-if="state.blockUI">
    <div class="o_spinner mb-4">
        <img src="/web/static/img/spin.svg" alt="Loading..."/>
    </div>
    <div class="o_progress_blockui" style="min-width: 500px;text-align: center">
        <div class="o_message text-center px-4">
            <t t-esc="state.line1"/> <br/>
            <t t-esc="state.line2"/>
        </div>
    </div>
  </t>
</div>`;
}

// -----------------------------------------------------------------------------
// RPC service adapted to handle progress reporting
// -----------------------------------------------------------------------------
export const rpcServiceProgress = {
    async: true,
    start(env) {
        let rpcId = 0;
        // redirect bus messages from OWL bus to the legacy bus
        env.bus.on("RPC:REQUEST", null, function(rId) {
            legacyEnv.bus.trigger('RPC:REQUEST', rId);
        });
        env.bus.on("RPC:RESPONSE", null, function(rId) {
            legacyEnv.bus.trigger('RPC:RESPONSE', rId);
        });
        // make sure the progress bar is registered in BlockUI
        registerProgressBarBLockUI();
        return function rpc(route, params = {}, settings) {
            var rId = rpcId++;
            // add progress_code to the context
            legacyProgressAjax.genericRelayEvents(route, 'call', params);
            return jsonrpc(env, rId, route, params, settings);
        };
    },
};

registry.category("services").remove("rpc");
registry.category("services").add("rpc", rpcServiceProgress);

// register the same disalog for CancelledProgress as there is for UserError
registry .category("error_dialogs")
    .add("odoo.addons.web_progress.models.web_progress.CancelledProgress",
        registry .category("error_dialogs").get("odoo.exceptions.UserError"))