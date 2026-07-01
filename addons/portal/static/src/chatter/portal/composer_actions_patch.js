import { composerActionsRegistry } from "@mail/core/common/composer_actions";

const existing = composerActionsRegistry.get("open-full-composer");
composerActionsRegistry.add(
    "open-full-composer",
    {
        ...existing,
        condition: ({ composer, owner }) =>
            !composer.message &&
            owner.props.showFullComposer &&
            composer.targetThread &&
            composer.targetThread.model !== "discuss.channel" &&
            !owner.portalChatter?.inFrontendPortalChatter(),
    },
    { force: true }
);
