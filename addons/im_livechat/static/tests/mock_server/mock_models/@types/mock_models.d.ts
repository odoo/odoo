declare module "mock_models" {
    import { LivechatChannel as LivechatChannel2 } from "../im_livechat_channel";
    import { LivechatChannelMemberHistory as LivechatChannelMemberHistory2 } from "../im_livechat_channel_member_history";

    export interface LivechatChannel extends LivechatChannel2 {}
    export interface LivechatChannelMemberHistory extends LivechatChannelMemberHistory2 {}

    export interface Models {
        "im_livechat.channel": LivechatChannel,
        "im_livechat.channel.member.history": LivechatChannelMemberHistory,
    }
}
