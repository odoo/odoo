declare module "models" {
    export interface Attachment {
        voice: Readonly<boolean>;
    }
    export interface Composer {
        voiceAttachment: Readonly<Attachment|undefined>;
    }
}
