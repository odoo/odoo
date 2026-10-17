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
    import { NamePlugin, nameService } from "@web/core/name_plugin";
    import { httpService } from "@web/core/network/http_service";
    import { NotificationPlugin } from "@web/core/notifications/notification_plugin";
    import { OfflinePlugin, offlineService } from "@web/core/offline/offline_plugin";
    import { overlayService } from "@web/core/overlay/overlay_plugin";
    import { popoverService } from "@web/core/popover/popover_plugin";
    import { TooltipPlugin, tooltipService } from "@web/core/tooltip/tooltip_plugin";
    import { UIPlugin, uiService } from "@web/core/ui/ui_plugin";
    import { SortablePlugin } from "@web/core/utils/sortable_plugin";
    import { publicInteractionService } from "@web/public/interaction_service";
    import { ViewPlugin, viewService } from "@web/views/view_plugin";
    import { ActionPlugin, actionService } from "@web/webclient/actions/action_plugin";
    import { profilingService } from "@web/webclient/debug/profiling/profiling_service";
    import { menuService } from "@web/webclient/menus/menu_service";
    import { LazySessionPlugin, lazySessionService } from "@web/webclient/lazy_session_plugin";
    import { shareTargetService } from "@web/webclient/share_target/share_target_service";
    import { BottomSheetPlugin } from "@web/core/bottom_sheet/bottom_sheet_plugin";
    import { ORM } from "@web/core/orm_plugin";
    import { OverlayPlugin } from "@web/core/overlay/overlay_plugin";
    import { PopoverPlugin } from "@web/core/popover/popover_plugin";

    type ExtractServiceFactory<T extends ServicesRegistryItemShape> = Awaited<ReturnType<T["start"]>>;
    export type ServiceFactories = {
        [P in keyof Services]: ExtractServiceFactory<Services[P]>;
    };
    export type PluginToService<T> = { start: () => T };

    export interface Services {
        "public.interactions": typeof publicInteractionService;
        action: PluginToService<ActionPlugin>;
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
        lazy_session: PluginToService<LazySessionPlugin>;
        menu: typeof menuService;
        name: PluginToService<NamePlugin>;
        notification: PluginToService<NotificationPlugin>;
        offline: PluginToService<OfflinePlugin>;
        orm: PluginToService<ORM>;
        overlay: PluginToService<OverlayPlugin>;
        popover: PluginToService<PopoverPlugin>;
        profiling: typeof profilingService;
        share_target: typeof shareTargetService;
        sortable: PluginToService<SortablePlugin>;
        title: PluginToService<TitlePlugin>;
        tooltip: PluginToService<TooltipPlugin>;
        ui: PluginToService<UIPlugin>;
        view: PluginToService<ViewPlugin>;
    }
}
