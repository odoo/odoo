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
        watchers: ["aw-watcher-afk", "aw-watcher-window"],
        installWeb: false,
        odooDomain: "",
        scriptGenerated: false,
        scriptText: "",
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

    // Event handlers
    toggleDev(ev) {
        this.state.isDev = ev.target.checked;
        if (!this.state.isDev) this.state.ideSelections = [];
    }

    toggleIDE(ev) {
        const ide = ev.target.value;
        if (ev.target.checked) {
            if (!this.state.ideSelections.includes(ide)) this.state.ideSelections.push(ide);
        } else {
            this.state.ideSelections = this.state.ideSelections.filter(i => i !== ide);
        }
    }

    toggleWatcher(ev) {
        const watcher = ev.target.value;
        if (ev.target.checked) {
            if (!this.state.watchers.includes(watcher)) this.state.watchers.push(watcher);
        } else {
            this.state.watchers = this.state.watchers.filter(w => w !== watcher);
        }
    }

    toggleWebWatcher(ev) {
        this.state.installWeb = ev.target.checked;
    }

    setOdooDomain(ev) {
        this.state.odooDomain = ev.target.value;
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

        // VSCode
        if (this.state.ideSelections.includes("vscode")) {
            lines.push('echo "Installing VSCode extension"');
            lines.push('if command -v code > /dev/null 2>&1; then');
            lines.push(`  sudo -u "$USER" code --install-extension ${VSCODE_EXT_ID}`);
            lines.push('else');
            lines.push('  echo "VSCode not found"');
            lines.push('fi');
            lines.push('');
        }

        // Chrome extension
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
        }

        // Start ActivityWatch
        lines.push('echo "Starting ActivityWatch"');
        lines.push('# Run aw-server (should fill the cors link from input field in odoo)');
        lines.push(`(cd "$INSTALL_DIR/activitywatch/aw-server" && ./aw-server --port 5700 &)`);
        lines.push('# Run aw-watcher-afk because with aw-server, they\'re buggy sometimes');
        if (this.state.watchers.includes("aw-watcher-afk")) lines.push('(cd "$INSTALL_DIR/activitywatch/aw-watcher-afk" && ./aw-watcher-afk &)');
        lines.push('# same to make sure they\'re working');
        if (this.state.watchers.includes("aw-watcher-window")) lines.push('(cd "$INSTALL_DIR/activitywatch/aw-watcher-window" && ./aw-watcher-window &)');
        lines.push('');
        lines.push('echo "Installation completed"');

        this.state.scriptText = lines.join("\n");
        this.state.scriptGenerated = true;
    }

}

ActivityWatchOnboarding.template = "hr_timesheet.OnboardingPage";
registry.category("actions").add("aw_onboarding", ActivityWatchOnboarding);
