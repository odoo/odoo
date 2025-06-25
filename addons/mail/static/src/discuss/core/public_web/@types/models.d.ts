declare module "models" {
    export interface Thread {
        displayInSidebar: boolean;
        from_message_id: Message;
        parent_channel_id: Thread;
        readonly hasSubChannelFeature: boolean;
        sub_channel_ids: Thread[];
    }
}
