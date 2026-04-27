declare module "mock_models" {
    import { WhatsAppComposer as WhatsAppComposer2 } from "@whatsapp/../tests/mock_server/mock_models/whatsapp_composer";
    import { WhatsAppMessage as WhatsAppMessage2 } from "@whatsapp/../tests/mock_server/mock_models/whatsapp_message";
    import { WhatsAppTemplate as WhatsAppTemplate2 } from "@whatsapp/../tests/mock_server/mock_models/whatsapp_template";

    export interface WhatsAppComposer extends WhatsAppComposer2 { }
    export interface WhatsAppMessage extends WhatsAppMessage2 { }
    export interface WhatsAppTemplate extends WhatsAppTemplate2 {}

    export interface Models {
        "whatsapp.composer": WhatsAppComposer,
        "whatsapp.message": WhatsAppMessage,
        "whatsapp.template": WhatsAppTemplate,
    }
}
