import type { CapacitorConfig } from "@capacitor/cli";

const appUrl = (process.env.KODOO_APP_URL || "https://kodoo.online").trim();
const cleartext = appUrl.startsWith("http://");

const config: CapacitorConfig = {
  appId: "online.kodoo.mobile",
  appName: "kodoo",
  webDir: "www",
  bundledWebRuntime: false,
  server: {
    url: appUrl,
    cleartext,
    allowNavigation: [
      "kodoo.online",
      "*.kodoo.online"
    ]
  },
  ios: {
    contentInset: "automatic",
    scrollEnabled: true
  },
  android: {
    allowMixedContent: false,
    captureInput: true,
    webContentsDebuggingEnabled: false
  },
  plugins: {
    SplashScreen: {
      launchAutoHide: true,
      backgroundColor: "#081320",
      showSpinner: false
    },
    StatusBar: {
      style: "DARK",
      backgroundColor: "#081320"
    }
  }
};

export default config;
