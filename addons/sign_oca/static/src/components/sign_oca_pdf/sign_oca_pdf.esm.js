/** @odoo-module Qweb **/
/* global navigator, console */

import SignOcaPdfCommon from "../sign_oca_pdf_common/sign_oca_pdf_common.esm.js";
import {registry} from "@web/core/registry";
import {renderToString} from "@web/core/utils/render";
const SignRegistry = registry.category("sign_oca");
import {useService} from "@web/core/utils/hooks";

export default class SignOcaPdf extends SignOcaPdfCommon {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this.to_sign = false;
    }
    async willStart() {
        await super.willStart(...arguments);
        this.checkFilledAll();
    }
    checkToSign() {
        this.props.updateControlPanel({
            cp_content: {
                $buttons: this.renderButtons(this.to_sign_update),
            },
        });
        this.to_sign = this.to_sign_update;
    }
    renderButtons(to_sign) {
        var $buttons = $(
            renderToString("oca_sign_oca.SignatureButtons", {
                to_sign: to_sign,
            })
        );
        $buttons.on("click.o_sign_oca_button_sign", () => {
            this.signOca();
        });
        return $buttons;
    }
    async getLocation() {
        if (!this.info.ask_location || !navigator.geolocation) {
            return {};
        }
        try {
            return await new Promise((resolve, reject) => {
                navigator.geolocation.getCurrentPosition(resolve, reject);
            });

            // Do something with the latitude and longitude
        } catch (error) {
            switch (error.code) {
                case error.PERMISSION_DENIED:
                    console.debug("User denied the request for geolocation.");
                    break;
                case error.POSITION_UNAVAILABLE:
                    console.debug("Location information is unavailable.");
                    break;
                case error.TIMEOUT:
                    console.debug("The request to get user location timed out.");
                    break;
                default:
                    console.debug("An unknown error occurred.");
                    break;
            }
        }
        return {};
    }
    async signOca() {
        const position = await this.getLocation();
        await this.orm.call(
            this.model,
            "action_sign",
            [[this.res_id], this.info.items],
            {
                latitude: position && position.coords && position.coords.latitude,
                longitude: position && position.coords && position.coords.longitude,
            }
        );
        this.props.trigger("history_back");
    }
    _trigger_up(ev) {
        const evType = ev.name;
        const payload = ev.data;
        if (evType === "call_service") {
            let args = payload.args || [];
            if (payload.service === "ajax" && payload.method === "rpc") {
                // Ajax service uses an extra 'target' argument for rpc
                args = args.concat(ev.target);
            }
            const service = this.env.services[payload.service];
            const result = service[payload.method].apply(service, args);
            payload.callback(result);
        } else if (evType === "get_session") {
            if (payload.callback) {
                payload.callback(this.env.session);
            }
        } else if (evType === "load_views") {
            const params = {
                model: payload.modelName,
                context: payload.context,
                views_descr: payload.views,
            };
            this.env.dataManager
                .load_views(params, payload.options || {})
                .then(payload.on_success);
        } else if (evType === "load_filters") {
            return this.env.dataManager.load_filters(payload).then(payload.on_success);
        } else {
            payload.__targetWidget = ev.target;
            this.trigger(evType.replace(/_/g, "-"), payload);
        }
    }
    postIframeField(item) {
        if (item.role_id === this.info.role_id) {
            var signatureItem = super.postIframeField(...arguments);
            signatureItem[0].append(
                SignRegistry.get(item.field_type).generate(this, item, signatureItem)
            );
            return signatureItem;
        }
    }
    checkFilledAll() {
        this.to_sign_update =
            Object.values(this.info.items).filter((item) => {
                return (
                    item.required &&
                    item.role_id === this.info.role_id &&
                    !SignRegistry.get(item.field_type).check(item)
                );
            }).length === 0;
        this.checkToSign();
    }
}
SignOcaPdf.props = {
    to_sign: {type: Boolean, optional: true},
};
