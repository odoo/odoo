declare module "models" {
    export type GloryRequestInfo = {
        requestName: string;
        responseName: string;
    };

    export type GlorySettings = {
        OccupyEnable: "0" | "1";
        SessionEnable: "0" | "1";
        SessionMinute: string;
        SoapDuplicateCheck: "0" | "1";
        SoapUserCheck: "0" | "1";
    };

    export type GloryUser = {
        id: string;
        session_id?: string;
        // The following are the user's permissions, we don't check these yet but may in the future
        admin: 0 | 1;
        cashout: 0 | 1;
        collect: 0 | 1;
        collect_banknote: 0 | 1;
        collect_both: 0 | 1;
        collect_coin: 0 | 1;
        collect_manual: 0 | 1;
        collect_towatermark: 0 | 1;
        collect_tozero: 0 | 1;
        collect_verify: 0 | 1;
        rbwULunlock: 0 | 1;
        rbwunlock: 0 | 1;
        rcwunlock: 0 | 1;
        refill: 0 | 1;
        replenishment: 0 | 1;
        sealing: 0 | 1;
    };

    export type GloryXmlElement =
        | string
        | {
              name: string;
              children?: GloryXmlElement[];
              attributes?: Record<string, string>;
          };

    export type SocketIoCallbacks = {
        onConnect: () => void;
        onClose: () => void;
        onEvent: (eventBody: any[]) => void;
        onBinaryEvent: (eventBody: Blob) => void;
    };
}
