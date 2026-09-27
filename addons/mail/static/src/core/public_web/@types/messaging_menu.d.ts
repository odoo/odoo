declare module "models" {
    export interface MessagingMenuTabFilter {
        compareChannels?: (c1: DiscussChannel, c2: DiscussChannel) => number;
        id: string;
        includesChannel?: (channel: DiscussChannel) => boolean;
        includesMessage?: (message: Message) => boolean;
        isDefault?: boolean;
        sequence?: number;
        text: string;
    }
}
