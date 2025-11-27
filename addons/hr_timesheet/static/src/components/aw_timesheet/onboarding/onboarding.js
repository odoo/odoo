/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";

export class ActivityWatchOnboarding extends Component {
    // OWL 2: state-driven
    state = useState({
        browser: this.detectBrowser(),
        os: this.detectOS(),
        isDev: false,
        ideSelections: [],
        installWeb: true,
    });

    // Browser & OS detection
    detectBrowser() {
        const ua = navigator.userAgent;
        if (ua.includes("Firefox")) return "Firefox";
        if (ua.includes("Edg/") || ua.includes("Edge/")) return "Edge";
        if (ua.includes("Chrome")) return "Chrome";
        if (ua.includes("Safari") && !ua.includes("Chrome")) return "Safari";
        return "Unknown";
    }

    detectOS() {
        const p = navigator.platform || navigator.userAgent;
        if (/Linux/.test(p)) return "Linux";
        if (/Mac|iPhone|iPad/.test(p)) return "macOS";
        if (/Win/.test(p)) return "Windows";
        return "Unknown";
    }

    toggleDev(ev) {
        this.state.isDev = ev.target.checked;
        if (!this.state.isDev) {
            this.state.ideSelections = [];
        }
    }

    toggleIDE(ev) {
        const ide = ev.target.value;
        if (ev.target.checked) {
            if (!this.state.ideSelections.includes(ide)) {
                this.state.ideSelections.push(ide);
            }
        } else {
            this.state.ideSelections = this.state.ideSelections.filter(i => i !== ide);
        }
    }

    toggleWebWatcher(ev) {
        this.state.installWeb = ev.target.checked;
    }

    generateScript() {
        const lines = [];
        const INSTALL_DIR="$HOME/Documents/RaoufTesting";
        const AW_URL="https://github.com/ActivityWatch/activitywatch/releases/download/v0.13.2/activitywatch-v0.13.2-linux-x86_64.zip";
        const VSCODE_EXT_ID="activitywatch.aw-watcher-vscode";
        const CHROME_EXT_ID="nglaklhklhcoonedhgnpgddginnjdadi";

        lines.push("#!/bin/bash");
        lines.push("set -e");
        lines.push('');
        lines.push('echo "Installing ActivityWatch - Raouf"');
        lines.push('');
        lines.push(`INSTALL_DIR="${INSTALL_DIR}"`);
        lines.push('mkdir -p "$INSTALL_DIR"');
        lines.push('cd "$INSTALL_DIR"');
        lines.push('');
        lines.push(`AW_URL="${AW_URL}"`);
        lines.push('echo "Downloading ActivityWatch"');
        lines.push('wget -O aw.zip "$AW_URL"');
        lines.push('echo "ActivityWatch Downloaded"');
        lines.push('unzip -o aw.zip');
        lines.push('rm aw.zip');
        lines.push('echo "ActivityWatch Unzipped"');
        lines.push('');
        lines.push('# for this poc, i\'m just focusing on chrome and vsCode on Linux, we will make it generic');

        if (this.state.ideSelections.includes("vscode")) {
            lines.push('echo "Installing VSCode extension"');
            lines.push('if command -v code > /dev/null 2>&1; then');
            lines.push(`  sudo -u "$USER" code --install-extension ${VSCODE_EXT_ID}`);
            lines.push('else');
            lines.push('  echo "VSCode not found"');
            lines.push('fi');
            lines.push('');
        }
        // should handle other ides

        if (this.state.installWeb) {
            lines.push('# important info to know, if the user uninstall the extension manually from the ui, it will move to the blocklist, and can\'t be installed again with this script');
            lines.push('# as google said on the doc: If the user uninstalls your extension, you should respect that decision.');
            lines.push('# ref: https://developer.chrome.com/docs/extensions/how-to/distribute/install-extensions#faq-uninstalls');
            lines.push('# we should just inform the user and give him the link to do it manually via https://chromewebstore.google.com/detail/activitywatch-web-watcher/nglaklhklhcoonedhgnpgddginnjdadi');
            lines.push('');
            lines.push('echo "Installing Chrome extension"');
            lines.push('declare -A EXTlist=( ["activitywatch-web-watcher"]="' + CHROME_EXT_ID + '" )');
            lines.push('mkdir -p /opt/google/chrome/extensions');
            lines.push('for i in "${!EXTlist[@]}"; do');
            lines.push('  echo \'{"external_update_url": "https://clients2.google.com/service/update2/crx"}\' | sudo tee /opt/google/chrome/extensions/${EXTlist[$i]}.json > /dev/null');
            lines.push('done');
            lines.push('echo "Chrome extension, restart Chrome and verify via chrome://extensions/"');
            lines.push('');
        } // should check the extension for other browsers

        // Start ActivityWatch
        lines.push('echo "Starting ActivityWatch"');
        const odooUrl = window.location.origin;
        // we need to check the conf file, it looks easier
        lines.push("cd activitywatch");
        lines.push("./aw-watcher-afk/aw-watcher-afk &");
        lines.push("./aw-watcher-window/aw-watcher-window &");
        lines.push(`./aw-server/aw-server --cors-origins ${odooUrl}`);
        lines.push("echo 'Installation completed'");

        const scriptText = lines.join("\n");
        const blob = new Blob([scriptText], { type: "text/plain" });
        const url = URL.createObjectURL(blob);

        const a = document.createElement("a");
        a.href = url;
        a.download = "start.sh";
        a.click();

        URL.revokeObjectURL(url);
    }
}

ActivityWatchOnboarding.template = "hr_timesheet.OnboardingPage";
registry.category("actions").add("aw_onboarding", ActivityWatchOnboarding);
