declare module "models" {
    export type GloryRequestInfo = {
        requestName: string;
        responseName: string;
    }

    export type GlorySettings = {
        OccupyEnable: "0"| "1";
        SessionEnable: "0" | "1";
        SessionMinute: string;
        SoapDuplicateCheck: "0" | "1";
        SoapUserCheck: "0" | "1";
    }

    export type GloryXmlElement = string |
    {
        name: string;
        children?: GloryXmlElement[];
        attributes?: Record<string, string>
    }

    export type SocketIoCallbacks = {
        onConnect: () => void;
        onEvent: (eventBody: any[]) => void;
        onBinaryEvent: (eventBody: Blob) => void
    }
}
