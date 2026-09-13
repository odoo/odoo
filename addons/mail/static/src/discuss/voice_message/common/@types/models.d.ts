declare module "models" {
    export interface Attachment {
        voice: Readonly<boolean>;
        voiceMetadata: Readonly<VoiceMetadata|undefined>;
    }
    export interface Composer {
        voiceAttachment: Readonly<Attachment|undefined>;
    }
}
