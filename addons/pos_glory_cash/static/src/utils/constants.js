import { _t } from "@web/core/l10n/translation";

/**
 * @type {import("models").GloryRequestInfo[]}
 */
export const WEBSOCKET_REQUESTS = {
    login: {
        requestName: "login request",
        responseName: "login response",
    },
    checkCredentials: {
        requestName: "check credential",
        responseName: "credential ok",
    },
    getSettings: {
        requestName: "getFunctionSetting",
        responseName: "sendFunctionSetting",
    },
    openSession: {
        requestName: "openSession",
        responseName: "sendSessionID",
    },
};

/**
 * @type {import("models").GloryRequestInfo[]}
 */
export const XML_REQUESTS = {
    getStatus: {
        requestName: "StatusRequest",
        responseName: "StatusResponse",
    },
    getInventory: {
        requestName: "InventoryRequest",
        responseName: "InventoryResponse",
    },
    startPayment: {
        requestName: "ChangeRequest",
        responseName: "ChangeResponse",
    },
    cancelPayment: {
        requestName: "ChangeCancelRequest",
        responseName: "ChangeCancelResponse",
    },
    collect: {
        requestName: "CollectRequest",
        responseName: "CollectResponse",
    },
    setDateAndTime: {
        requestName: "AdjustTimeRequest",
        responseName: "AdjustTimeResponse",
    },
    reset: {
        requestName: "ResetRequest",
        responseName: "ResetResponse",
    },
    occupy: {
        requestName: "OccupyRequest",
        responseName: "OccupyResponse",
    },
    release: {
        requestName: "ReleaseRequest",
        responseName: "ReleaseResponse",
    },
};

// See p198 of the IF Specification document, "StatusChangeNotification"
export const GLORY_STATUS = {
    0: "INITIALIZING",
    1: "IDLE",
    2: "STARTING_PAYMENT",
    3: "WAITING_PAYMENT",
    4: "COUNTING",
    5: "DISPENSING",
    6: "WAITING_CASH_IN_REMOVE",
    7: "WAITING_CASH_OUT_REMOVE",
    8: "RESETTING",
    9: "CANCELLING",
    10: "CALCULATING_CHANGE",
    11: "DEPOSIT_CANCEL",
    12: "COLLECTING",
    13: "ERROR",
    14: "UPLOAD_FIRMWARE",
    15: "READING_LOG",
    16: "WAITING_REPLENISHMENT",
    17: "COUNTING_REPLENISHMENT",
    18: "UNLOCKING",
    19: "WAITING_INVENTORY",
    20: "FIXED_DEPOSIT",
    21: "FIXED_DISPENSE",
    22: "WAITING_DISPENSE",
    23: "WAITING_CANCEL",
    24: "CATEGORY2_NOTE",
    25: "WAITING_DEPOSIT",
    26: "WAITING_COFT_REMOVAL",
    27: "SEALING",
    30: "WAITING_ERROR_RECOVERY",
    40: "PROGRAM_BUSY",
    41: "WAITING_UPDATE",
};

export const GLORY_STATUS_STRING = {
    DISCONNECTED: _t("Disconnected"),
    BAD_CREDENTIALS: _t("Failed to authenticate"),
    INITIALIZING: _t("Initializing"),
    IDLE: _t("Idle"),
    STARTING_PAYMENT: _t("Starting payment"),
    WAITING_PAYMENT: _t("Waiting for insertion of cash"),
    COUNTING: _t("Counting"),
    COUNTING_REPLENISHMENT: _t("Counting replenished cash"),
    COLLECTING: _t("Collection in progress"),
    ERROR: _t("Error"),
    DISPENSING: _t("Dispensing"),
    WAITING_CASH_IN_REMOVE: _t("Waiting for cash to be removed"),
    WAITING_CASH_OUT_REMOVE: _t("Waiting for cash to be removed"),
    WAITING_COFT_REMOVAL: _t("Waiting for coin overflow removal"),
    WAITING_REPLENISHMENT: _t("Waiting for cash to be replenished"),
    RESETTING: _t("Resetting"),
    CANCELLING: _t("Cancelling payment"),
    CALCULATING_CHANGE: _t("Calculating change"),
    WAITING_INVENTORY: _t("Waiting for inventory"),
    FIXED_DEPOSIT: _t("Dispensing"),
    FIXED_DISPENSE: _t("Dispensing"),
    WAITING_CANCEL: _t("Waiting for cancellation"),
    WAITING_ERROR_RECOVERY: _t("Waiting for error recovery"),
};

// See p51 of the IF Specification document, "ChangeResponse"
export const GLORY_RESULT = {
    0: "SUCCESS",
    1: "CANCEL",
    2: "RESET",
    3: "OCCUPIED_BY_OTHER",
    4: "OCCUPATION_NOT_AVAILABLE",
    5: "NOT_OCCUPIED",
    6: "DESIGNATION_SHORTAGE",
    9: "CANCEL_CHANGE_SHORTAGE",
    10: "CHANGE_SHORTAGE",
    11: "EXCLUSIVE_ERROR",
    12: "CHANGE_INCONSISTENCY",
    13: "AUTO_RECOVERY_FAILURE",
    15: "USER_AUTHENTICATION_FAILURE",
    16: "NUMBER_OF_SESSION_OVER",
    17: "OCCUPIED_BY_SELF",
    20: "SESSION_NOT_AVAILABLE",
    21: "INVALID_SESSION",
    22: "SESSION_TIMEOUT",
    26: "MANUAL_DEPOSIT_DISAGREEMENT",
    32: "VERIFY_COLLECT_FAILED",
    33: "ILLEGAL_DENOMINATION",
    34: "STACKER_CAPACITY_SHORTAGE",
    35: "CI_SERVER_COMMUNICATION_ERROR",
    36: "NUMBER_OF_REGISTRATION_OVER",
    40: "INVALID_CASSETTE_NUMBER",
    41: "IMPROPER_CASSETTE",
    43: "EXCHANGE_RATE_ERROR",
    44: "COUNTED_CATEGORY_2_3",
    45: "UPPER_LIMIT_AMOUNT_OVER",
    46: "PASSWORD_EXPIRED",
    96: "DUPLICATE_TRANSACTION",
    98: "PARAMETER_ERROR",
    99: "PROGRAM_ERROR",
    100: "DEVICE_ERROR",
};

// See p77 of the IF Specification document, "InventoryResponse"
export const GLORY_CURRENCY_STATUS = {
    0: "EMPTY",
    1: "NEAR_EMPTY",
    2: "EXIST",
    3: "NEAR_FULL",
    4: "FULL",
    21: "MISSING",
    22: "NA",
};
