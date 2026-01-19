import {
    mailDataHelpers,
    parseRequestParams,
    registerRoute,
} from "@mail/../tests/mock_server/mail_mock_server";
import { Command, makeKwArgs, serverState } from "@web/../tests/web_test_helpers";
import { loadBundle } from "@web/core/assets";
import { patch } from "@web/core/utils/patch";

/**
 * @template [T={}]
 * @typedef {import("@web/../tests/web_test_helpers").RouteCallback<T>} RouteCallback
 */

registerRoute("/im_livechat/get_session", get_session);
/** @type {RouteCallback} */
async function get_session(request) {
    /** @type {import("mock_models").DiscussChannel} */
    const DiscussChannel = this.env["discuss.channel"];
    /** @type {import("mock_models").LivechatChannel} */
    const LivechatChannel = this.env["im_livechat.channel"];
    /** @type {import("mock_models").ResCountry} */
    const ResCountry = this.env["res.country"];
    /** @type {import("mock_models").ResPartner} */
    const ResPartner = this.env["res.partner"];
    /** @type {import("mock_models").ResUsers} */
    const ResUsers = this.env["res.users"];

    let {
        channel_id,
        previous_operator_id,
        persisted,
        context = {},
    } = await parseRequestParams(request);
    previous_operator_id = parseInt(previous_operator_id);
    const agent = LivechatChannel._get_operator(channel_id, previous_operator_id);
    if (!agent) {
        return false;
    }
    let country_id;
    if (this.env.user && !ResUsers._is_public(this.env.uid)) {
        country_id = this.env.user.country_id;
    } else if (context.mockedCountryCode) {
        // simulate geoip
        const country = ResCountry._filter([["code", "=", context.mockedCountryCode]])[0];
        if (country) {
            country_id = country.id;
        }
    }
    if (!persisted) {
        const store = new mailDataHelpers.Store();
        ResUsers._init_store_data(store);
        store.add("discuss.channel", {
            channel_type: "livechat",
            fetchChannelInfoState: "fetched",
            id: -1,
            isLoaded: true,
            livechat_operator_id: mailDataHelpers.Store.one(
                ResPartner.browse(agent.partner_id),
                makeKwArgs({ fields: ["avatar_128", "user_livechat_username"] })
            ),
            scrollUnread: false,
        });
        return { store_data: store.get_result(), channel_id: -1 };
    }
    const channelVals = LivechatChannel._get_livechat_discuss_channel_vals(channel_id, {
        agent: agent,
    });
    channelVals.country_id = country_id;
    const channelId = DiscussChannel.create(channelVals);
    const store = new mailDataHelpers.Store();
    ResUsers._init_store_data(store);
    store.add(DiscussChannel.browse(channelId));
    store.add(DiscussChannel.browse(channelId), {
        isLoaded: true,
        scrollUnread: false,
    });
    return { store_data: store.get_result(), channel_id: channelId };
}

registerRoute("/im_livechat/visitor_leave_session", visitor_leave_session);
/** @type {RouteCallback} */
async function visitor_leave_session(request) {
    /** @type {import("mock_models").DiscussChannel} */
    const DiscussChannel = this.env["discuss.channel"];

    const { channel_id } = await parseRequestParams(request);
    const [channel] = DiscussChannel.search_read([["id", "=", channel_id]]);
    if (!channel) {
        return;
    }
    DiscussChannel._close_livechat_session(channel_id);
}
registerRoute("/im_livechat/feedback", feedback);
/** @type {RouteCallback} */
async function feedback(request) {
    /** @type {import("mock_models").DiscussChannel} */
    const DiscussChannel = this.env["discuss.channel"];
    /** @type {import("mock_models").RatingRating} */
    const RatingRating = this.env["rating.rating"];

    const { channel_id, rate, reason } = await parseRequestParams(request);
    let [channel] = DiscussChannel.search_read([["id", "=", channel_id]]);
    if (!channel) {
        return false;
    }
    const values = {
        rating: rate,
        consumed: true,
        feedback: reason,
        is_internal: false,
        res_id: channel.id,
        res_model: "discuss.channel",
        rated_partner_id: channel.channel_partner_ids[0],
    };
    if (channel.rating_ids.length === 0) {
        RatingRating.create(values);
    } else {
        RatingRating.write([channel.rating_ids[0]], values);
    }
    [channel] = DiscussChannel.search_read([["id", "=", channel_id]]);
    return channel.rating_ids[0];
}

registerRoute("/im_livechat/init", livechat_init);
/** @type {RouteCallback} */
async function livechat_init(request) {
    return {
        available_for_me: true,
        rule: {},
    };
}

registerRoute("/im_livechat/email_livechat_transcript", email_livechat_transcript);
/** @type {RouteCallback} */
async function email_livechat_transcript(request) {
    const DiscussChannel = this.env["discuss.channel"];
    const { channel_id, email } = await parseRequestParams(request);
    const [channel] = DiscussChannel.search_read([["id", "=", channel_id]]);
    if (!channel) {
        return;
    }
    DiscussChannel._email_livechat_transcript(channel_id, email);
}

registerRoute("/im_livechat/emoji_bundle", get_emoji_bundle);
/** @type {RouteCallback} */
async function get_emoji_bundle(request) {
    await loadBundle("web.assets_emoji");
    return new Response();
}

registerRoute("/im_livechat/session/update_status", session_update_status);
/** @type {RouteCallback} */
async function session_update_status(request) {
    /** @type {import("mock_models").DiscussChannel} */
    const DiscussChannel = this.env["discuss.channel"];
    const { channel_id, livechat_status } = await parseRequestParams(request);
    if (this.env.user.share) {
        return false;
    }
    const [channel] = DiscussChannel.search_read([["id", "=", channel_id]]);
    if (!channel) {
        return false;
    }
    DiscussChannel.write([channel_id], {
        livechat_status: livechat_status,
    });
    return true;
}

registerRoute("/im_livechat/session/update_note", session_update_note);
/** @type {RouteCallback} */
async function session_update_note(request) {
    /** @type {import("mock_models").DiscussChannel} */
    const DiscussChannel = this.env["discuss.channel"];
    const { channel_id, note } = await parseRequestParams(request);
    if (this.env.user.share) {
        return false;
    }
    const [channel] = DiscussChannel.search_read([["id", "=", channel_id]]);
    if (!channel) {
        return false;
    }
    DiscussChannel.write([channel_id], {
        livechat_note: note,
    });
    return true;
}

registerRoute("/im_livechat/conversation/write_expertises", livechat_conversation_write_expertises);
/** @type {RouteCallback} */
async function livechat_conversation_write_expertises(request) {
    /** @type {import("mock_models").DiscussChannel} */
    const DiscussChannel = this.env["discuss.channel"];
    const { channel_id, orm_commands } = await parseRequestParams(request);
    const [channel] = DiscussChannel.search_read([["id", "=", channel_id]]);
    if (!channel) {
        return false;
    }
    DiscussChannel.write(channel_id, { livechat_expertise_ids: orm_commands });
}

registerRoute(
    "/im_livechat/conversation/create_and_link_expertise",
    livechat_conversation_create_and_link_expertise
);
/** @type {RouteCallback} */
async function livechat_conversation_create_and_link_expertise(request) {
    /** @type {import("mock_models").DiscussChannel} */
    const DiscussChannel = this.env["discuss.channel"];
    /** @type {import("mock_models").ImLivechatExpertise} */
    const ImLivechatExpertise = this.env["im_livechat.expertise"];
    const { channel_id, expertise_name } = await parseRequestParams(request);
    const [channel] = DiscussChannel.search([["id", "=", channel_id]]);
    if (!channel) {
        return false;
    }
    const [expertise] = ImLivechatExpertise.search([["name", "=", expertise_name]]);
    let expertiseId = expertise?.id;
    if (!expertise) {
        expertiseId = ImLivechatExpertise.create({ name: expertise_name });
    }
    DiscussChannel.write(channel_id, { livechat_expertise_ids: [Command.link(expertiseId)] });
}

patch(mailDataHelpers, {
    _process_request_for_all(store, name, params) {
        const ResPartner = this.env["res.partner"];
        const ResUsers = this.env["res.users"];
        super._process_request_for_all(...arguments);
        store.add({ livechat_available: true });
        if (name === "init_livechat") {
            if (this.env.user && !ResUsers._is_public(this.env.uid)) {
                store.add(
                    ResPartner.browse(this.env.user.partner_id),
                    makeKwArgs({ fields: ["email"] })
                );
            }
        }
    },
    _process_request_for_internal_user(store, name, params) {
        super._process_request_for_internal_user(...arguments);
        if (name === "im_livechat.channel") {
            const LivechatChannel = this.env["im_livechat.channel"];
            store.add(
                LivechatChannel.browse(LivechatChannel.search([])),
                makeKwArgs({ fields: ["are_you_inside", "name"] })
            );
            return;
        }
        if (name === "/im_livechat/looking_for_help") {
            const DiscussChannel = this.env["discuss.channel"];
            store.add(
                DiscussChannel.browse(
                    DiscussChannel.search([["livechat_status", "=", "need_help"]])
                )
            );
        }
        if (name === "/im_livechat/fetch_self_expertise") {
            const ResUsers = this.env["res.users"];
            store.add(ResUsers.browse(serverState.userId), ["livechat_expertise_ids"]);
        }
    },
});
