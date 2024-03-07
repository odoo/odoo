import { parseRequestParams, registerRoute } from "@mail/../tests/mock_server/mail_mock_server";
import { Discuss } from "@mail/core/common/discuss";

/**
 * @template [T={}]
 * @typedef {import("@web/../tests/web_test_helpers").RouteCallback<T>} RouteCallback
 */

registerRoute("/im_livechat/get_session", get_session);
/** @type {RouteCallback} */
async function get_session(request) {
    /** @type {import("mock_models").DiscussChannel} */
    const DiscussChannel = this.env["discuss.channel"];
    /** @type {import("mock_models").DiscussChannelMember} */
    const DiscussChannelMember = this.env["discuss.channel.member"];
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
        anonymous_name,
        previous_operator_id,
        persisted,
        context = {},
    } = await parseRequestParams(request);
    let country_id;
    // don't use the anonymous name if the user is logged in
    if (this.env.user && !ResUsers._is_public(this.env.uid)) {
        country_id = this.env.user.country_id;
    } else {
        // simulate geoip
        const countryCode = context.mockedCountryCode;
        const country = ResCountry._filter([["code", "=", countryCode]])[0];
        if (country) {
            country_id = country.id;
            anonymous_name = anonymous_name + " (" + country.name + ")";
        }
    }
    const channelVals = LivechatChannel._get_livechat_discuss_channel_vals(
        channel_id,
        anonymous_name,
        previous_operator_id,
        country_id,
        persisted
    );
    if (!channelVals) {
        return false;
    }
    if (!persisted) {
        const [operatorPartner] = ResPartner.search_read([
            ["id", "=", channelVals.livechat_operator_id],
        ]);
        const res = ResUsers._init_store_data();
        return Object.assign(res, {
            Thread: {
                id: -1,
                model: "discuss.channel",
                isLoaded: true,
                name: channelVals["name"],
                chatbot_current_step_id: channelVals.chatbot_current_step_id,
                state: "open",
                operator: ResPartner.mail_partner_format([operatorPartner.id])[operatorPartner.id],
                channel_type: "livechat",
            },
        });
    }
    const channelId = DiscussChannel.create(channelVals);
    DiscussChannel._find_or_create_persona_for_channel(channelId, "Visitor");
    const [guestMemberId] = DiscussChannelMember.search([
        ["channel_id", "=", channelId],
        ["guest_id", "!=", false],
    ]);
    DiscussChannelMember.write([guestMemberId], { fold_state: "open" });
    const res = ResUsers._init_store_data();
    return Object.assign(res, {
        Thread: {
            isLoaded: true,
            ...DiscussChannel._channel_info([channelId])[0],
        },
    });
}

registerRoute("/im_livechat/notify_typing", notify_typing);
/** @type {RouteCallback} */
async function notify_typing(request) {
    /** @type {import("mock_models").DiscussChannel} */
    const DiscussChannel = this.env["discuss.channel"];
    /** @type {import("mock_models").DiscussChannelMember} */
    const DiscussChannelMember = this.env["discuss.channel.member"];

    const { channel_id, is_typing } = await parseRequestParams(request);
    const [channel] = DiscussChannel.search_read([["id", "=", channel_id]]);
    const memberOfCurrentUser = DiscussChannel._find_or_create_member_for_self(channel.id);
    DiscussChannelMember.notify_typing([memberOfCurrentUser.id], is_typing);
}

registerRoute("/im_livechat/visitor_leave_session", visitor_leave_session);
/** @type {RouteCallback} */
async function visitor_leave_session(request) {
    /** @type {import("mock_models").DiscussChannel} */
    const DiscussChannel = this.env["discuss.channel"];

    const { channel_id } = await parseRequestParams(request);
    const channel = DiscussChannel.search_read([["id", "=", channel_id]]);
    if (!channel) {
        return;
    }
    DiscussChannel._close_livechat_session(channel);
}

registerRoute("/im_livechat/feedback", feedback);
/** @type {RouteCallback} */
async function feedback(request) {
    /** @type {import("mock_models").DiscussChannel} */
    const DiscussChannel = this.env["discuss.channel"];
    /** @type {import("mock_models").RatingRating} */
    const RatingRating = this.env["rating.rating"];

    const { channel_id, rate, reason } = await parseRequestParams(request);
    let [channel] = Discuss.search_read([["id", "=", channel_id]]);
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

registerRoute("/im_livechat/chat_history", chat_history);
/** @type {RouteCallback} */
async function chat_history(request) {
    /** @type {import("mock_models").DiscussChannel} */
    const DiscussChannel = this.env["discuss.channel"];

    const { channel_id, last_id, limit = 20 } = await parseRequestParams(request);
    const [channel] = DiscussChannel.search_read([["id", "=", channel_id]]);
    if (!channel) {
        return [];
    }
    return DiscussChannel._channel_fetch_message(channel.id, last_id, limit);
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
    return true;
}
