import { useConfig, Plugin, t } from "@odoo/owl";

export class MeetingPlugin extends Plugin {
    openChat = useConfig("openChat", t.function());
}
