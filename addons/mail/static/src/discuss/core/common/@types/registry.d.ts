declare module "registries" {
    import { DiscussChannel, Store } from "models";

    interface ChannelCommandShape {
        condition: (params: { store: Store, channel: DiscussChannel }) => boolean;
        help: TranslatableString;
        methodName?: string;
        onExecute?: (channel: DiscussChannel) => void | Promise<void>;
    }

    interface GlobalRegistryCategories {
        "discuss.channel_commands": ChannelCommandShape;
    }
}
