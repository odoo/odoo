const VIVA_APP_STORAGE_KEY = "vivawallet_app_answer";

export const isAndroidDevice = () => navigator.userAgent.toLowerCase().includes("android");

/**
 * Whether the payments of Viva.com methods are made with the Viva app installed
 * on this device instead of the configured terminal. This is a device setting,
 * chosen in the default payment method popup.
 */
export const isVivaAppEnabled = () => window.localStorage.getItem(VIVA_APP_STORAGE_KEY) === "true";

export const setVivaAppEnabled = (enabled) =>
    window.localStorage.setItem(VIVA_APP_STORAGE_KEY, enabled ? "true" : "false");
