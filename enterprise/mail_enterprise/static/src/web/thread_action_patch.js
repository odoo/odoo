import { threadActionsRegistry } from "@mail/core/common/thread_actions";

threadActionsRegistry.get("expand-discuss").shouldClearBreadcrumbs = (component) => {
    return component.homeMenuService.hasHomeMenu;
};
