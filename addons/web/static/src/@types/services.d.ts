declare module "services" {
    import { ServicesRegistryItemShape } from "registries";

    import { TitlePlugin } from "@web/core/browser/title_plugin";
    import { commandService } from "@web/core/commands/command_service";
    import { datetimePickerService } from "@web/core/datetime/datetimepicker_service";
    import { DialogPlugin } from "@web/core/dialog/dialog_plugin";
    import { EffectPlugin } from "@web/core/effects/effect_plugin";
    import { FrequentEmojiPlugin } from "@web/core/emoji_picker/frequent_emoji_plugin";
    import { fieldService } from "@web/core/field_service";
    import { fileUploadService } from "@web/core/file_upload/file_upload_service";
    import { HotkeyPlugin } from "@web/core/hotkeys/hotkey_plugin";
    import { Localization } from "@web/core/l10n/localization";
    import { nameService } from "@web/core/name_service";
    import { httpService } from "@web/core/network/http_service";
    import { NotificationPlugin } from "@web/core/notifications/notification_plugin";
    import { offlineService } from "@web/core/offline/offline_plugin";
    import { ORM } from "@web/core/orm_plugin";
    import { OverlayPlugin } from "@web/core/overlay/overlay_plugin";
    import { PopoverPlugin } from "@web/core/popover/popover_plugin";
    import { BottomSheetPlugin } from "@web/core/bottom_sheet/bottom_sheet_plugin";
    import { tooltipService } from "@web/core/tooltip/tooltip_service";
    import { uiService } from "@web/core/ui/ui_plugin";
    import { SortablePlugin } from "@web/core/utils/sortable_plugin";
    import { publicInteractionService } from "@web/public/interaction_service";
    import { viewService } from "@web/views/view_service";
    import { actionService } from "@web/webclient/actions/action_service";
    import { profilingService } from "@web/webclient/debug/profiling/profiling_service";
    import { menuService } from "@web/webclient/menus/menu_service";
    import { lazySession } from "@web/webclient/session_service";
    import { shareTargetService } from "@web/webclient/share_target/share_target_service";

    type ExtractServiceFactory<T extends ServicesRegistryItemShape> = Awaited<ReturnType<T["start"]>>;
    export type ServiceFactories = {
        [P in keyof Services]: ExtractServiceFactory<Services[P]>;
    };
    export type PluginToService<T> = { start: () => T };

    export interface Services {
        "public.interactions": typeof publicInteractionService;
        action: typeof actionService;
        bottom_sheet: PluginToService<BottomSheetPlugin>;
        command: typeof commandService;
        datetime_picker: typeof datetimePickerService;
        dialog: PluginToService<DialogPlugin>;
        effect: PluginToService<EffectPlugin>;
        field: typeof fieldService;
        file_upload: typeof fileUploadService;
        frequent_emoji: PluginToService<FrequentEmojiPlugin>;
        hotkey: PluginToService<HotkeyPlugin>;
        http: typeof httpService;
        lazy_session: typeof lazySession;
        localization: PluginToService<Localization>;
        menu: typeof menuService;
        name: typeof nameService;
        notification: PluginToService<NotificationPlugin>;
        offline: typeof offlineService;
        orm: PluginToService<ORM>;
        overlay: PluginToService<OverlayPlugin>;
        popover: PluginToService<PopoverPlugin>;
        profiling: typeof profilingService;
        share_target: typeof shareTargetService;
        sortable: PluginToService<SortablePlugin>;
        title: PluginToService<TitlePlugin>;
        tooltip: typeof tooltipService;
        ui: typeof uiService;
        view: typeof viewService;
    }
}
