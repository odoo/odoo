declare module "models" {
    import { DiscussChannel as DiscussChannelClass } from "@mail/discuss/core/common/discuss_channel_model";

    export interface DiscussChannel extends Patch<DiscussChannelClass, typeof import("@im_livechat/embed/cors/discuss_channel_model_patch").discussChannelPatch, "transcriptUrl"> {}
}
