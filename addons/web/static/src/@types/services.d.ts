declare module "services" {
    import { ServicesRegistryShape } from "registries";

    import { commandService } from "@web/core/commands/command_service";
    import { datetimePickerService } from "@web/core/datetime/datetimepicker_service";
    import { dialogService } from "@web/core/dialog/dialog_plugin";
    import { effectService } from "@web/core/effects/effect_plugin";
    import { fieldService } from "@web/core/field_service";
    import { fileUploadService } from "@web/core/file_upload/file_upload_service";
    import { hotkeyService } from "@web/core/hotkeys/hotkey_plugin";
    import { nameService } from "@web/core/name_service";
    import { httpService } from "@web/core/network/http_service";
    import { notificationService } from "@web/core/notifications/notification_plugin";
    import { offlineService } from "@web/core/offline/offline_plugin";
    import { overlayService } from "@web/core/overlay/overlay_plugin";
    import { popoverService } from "@web/core/popover/popover_plugin";
    import { tooltipService } from "@web/core/tooltip/tooltip_service";
    import { uiService } from "@web/core/ui/ui_plugin";
    import { sortableService } from "@web/core/utils/sortable_plugin";
    import { publicInteractionService } from "@web/public/interaction_service";
    import { viewService } from "@web/views/view_plugin";
    import { actionService } from "@web/webclient/actions/action_service";
    import { profilingService } from "@web/webclient/debug/profiling/profiling_service";
    import { menuService } from "@web/webclient/menus/menu_service";
    import { lazySession } from "@web/webclient/session_service";
    import { shareTargetService } from "@web/webclient/share_target/share_target_service";

    type ExtractServiceFactory<T extends ServicesRegistryShape> = Awaited<ReturnType<T["start"]>>;
    export type ServiceFactories = {
        [P in keyof Services]: ExtractServiceFactory<Services[P]>;
    };

    export interface Services {
        "public.interactions": typeof publicInteractionService;
        action: typeof actionService;
        command: typeof commandService;
        datetime_picker: typeof datetimePickerService;
        dialog: typeof dialogService;
        effect: typeof effectService;
        field: typeof fieldService;
        file_upload: typeof fileUploadService;
        hotkey: typeof hotkeyService;
        http: typeof httpService;
        lazy_session: typeof lazySession;
        menu: typeof menuService;
        name: typeof nameService;
        notification: typeof notificationService;
        offline: typeof offlineService;
        overlay: typeof overlayService;
        popover: typeof popoverService;
        profiling: typeof profilingService;
        share_target: typeof shareTargetService;
        sortable: typeof sortableService;
        tooltip: typeof tooltipService;
        ui: typeof uiService;
        view: typeof viewService;
    }
}
