import { rpc } from "@web/core/network/rpc";
import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";
import { session } from "@web/session";
import { PosStore } from "@point_of_sale/app/store/pos_store";

/**
 * In this file we perform the necessary patches to make some of the web views work offline.
 */

patch(rpc, {
    _rpc(route, params = {}, settings = {}) {
        if (!navigator.onLine) {
            if (
                session.posCache?.[params.model] &&
                Object.hasOwn(session.posCache[params.model], params.method)
            ) {
                return new Promise((resolve) =>
                    resolve(session.posCache[params.model][params.method])
                );
            }
        }
        return super._rpc(...arguments);
    },
});
patch(ListController.prototype, {
    async openRecord(record) {
        if (navigator.onLine) {
            return super.openRecord(...arguments);
        }
        const activeIds = this.model.root.records.map((datapoint) => datapoint.resId);
        this.props.selectRecord(record.resId, { activeIds });
    },
});
patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        const webSearchReadResult = await this.data.orm.call("pos.order", "web_search_read", [], {
            specification: {
                currency_id: {
                    fields: {},
                },
                name: {},
                session_id: {
                    fields: {
                        display_name: {},
                    },
                },
                date_order: {},
                config_id: {
                    fields: {
                        display_name: {},
                    },
                },
                pos_reference: {},
                tracking_number: {},
                partner_id: {
                    fields: {
                        display_name: {},
                    },
                },
                user_id: {
                    fields: {
                        display_name: {},
                    },
                },
                amount_total: {},
                state: {},
                is_edited: {},
            },
            offset: 0,
            limit: 80,
            context: {
                // lang: "en_US",
                // tz: Europe / Brussels,
                // uid: 2,
                // allowed_company_ids: [1],
                // bin_size: true,
                // current_company_id: 1,
            },
            count_limit: 10001,
            domain: [
                [
                    "config_id",
                    "in",
                    [this.config.id, ...this.config.trusted_config_ids.map((x) => x.id)],
                ],
            ],
        });
        this.data.read(
            "pos.order",
            webSearchReadResult.records.map((x) => x.id)
        );
        session.posCache = {
            "pos.order": {
                web_search_read: webSearchReadResult,
                get_views: await this.data.orm.call("pos.order", "get_views", [], {
                    views: [
                        [false, "list"],
                        [session.view_ids.view_pos_order_filter, "search"],
                    ],
                }),
            },
            "res.users": {
                has_group: false,
            },
        };
    },
});
