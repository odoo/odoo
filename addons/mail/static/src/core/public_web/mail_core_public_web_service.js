import { registry } from "@web/core/registry";

export const mailCorePublicWebService = {
    dependencies: ["mail.store"],
    /**
     * @param {import("@web/env").OdooEnv}
     * @param {Partial<import("services").Services>} services
     */
    start(env, services) {
        services["mail.store"].ensureInitialized();
        env.bus.addEventListener(
            "discuss.channel/new_message",
            ({ detail: { channel, message, silent } }) => {
                if (env.services.ui.isSmall || message.isSelfAuthored || silent) {
                    return;
                }
                channel.notifyMessageToUser(message);
            }
        );
    },
};

registry.category("services").add("mail.core.public.web", mailCorePublicWebService);
