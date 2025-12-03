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
        if (ua.includes("Firefox")) {
            return "Firefox";
        }
        if (ua.includes("Edg/") || ua.includes("Edge/")) {
            return "Edge";
        }
        if (ua.includes("Chrome")) {
            return "Chrome";
        }
        if (ua.includes("Safari") && !ua.includes("Chrome")) {
            return "Safari";
        }
        return "Unknown";
    }

    detectOS() {
        const p = navigator.platform || navigator.userAgent;
        if (/Linux/.test(p)) {
            return "Linux";
        }
        if (/Mac|iPhone|iPad/.test(p)) {
            return "macOS";
        }
        if (/Win/.test(p)) {
            return "Windows";
        }
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
            this.state.ideSelections = this.state.ideSelections.filter((i) => i !== ide);
        }
    }

    getVsCodeBasedExtensionScript(ide) {
        return [
            `# Install ${ide} extension`,
            `if command -v ${ide} > /dev/null 2>&1; then`,
            `  sudo -u "$USER" ${ide} --install-extension activitywatch.aw-watcher-vscode`,
            "else",
            `  echo \"${ide} not found\"`,
            "fi",
            "",
        ].join("\n");
    }

    toggleWebWatcher(ev) {
        this.state.installWeb = ev.target.checked;
    }

    generateScript() {
        const odooUrl = window.location.origin;
        const lines = [
            "#!/bin/bash",
            "set -e",
            "",
            'echo "Installing ActivityWatch - Raouf"',
            "pkill aw-",
            "",
            'INSTALL_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/activitywatch"',
            'WATCHERS_DIR="$INSTALL_DIR/activitywatch"',
            'WRAPPER_SCRIPT="$INSTALL_DIR/start_watchers.sh"',
            'LOG_FILE="$INSTALL_DIR/startup.log"',
            "",
            'mkdir -p "$INSTALL_DIR"',
            'cd "$INSTALL_DIR"',
            "",
            "# Download AW",
            'AW_URL="https://github.com/ActivityWatch/activitywatch/releases/download/v0.13.2/activitywatch-v0.13.2-linux-x86_64.zip"',
            'echo "Downloading ActivityWatch"',
            'wget -O aw.zip "$AW_URL"',
            'echo "ActivityWatch Downloaded"',
            "unzip -o aw.zip",
            "rm aw.zip",
            'echo "ActivityWatch Unzipped"',
            "",
        ];

        // for this poc, i'm just focusing on chrome and vsCode on Linux, we will make it generic
        for (const vsCodeBasedIde of ["code", "codium", "antigravity"]) {
            // can be extended later
            if (this.state.ideSelections.includes(vsCodeBasedIde)) {
                lines.push(this.getVsCodeBasedExtensionScript(vsCodeBasedIde));
            }
        }

        // important info to know, if the user uninstall the extension manually from the ui, it will move to the blocklist, and can't be installed again with this script
        // as google said on the doc: If the user uninstalls your extension, you should respect that decision.
        // ref: https://developer.chrome.com/docs/extensions/how-to/distribute/install-extensions#faq-uninstalls
        // we should just inform the user and give him the link to do it manually via https://chromewebstore.google.com/detail/activitywatch-web-watcher/nglaklhklhcoonedhgnpgddginnjdadi
        if (this.state.installWeb) {
            lines.push(
                "# Install Chrome extension",
                'declare -A EXTlist=( ["activitywatch-web-watcher"]="nglaklhklhcoonedhgnpgddginnjdadi" )',
                "sudo mkdir -p /opt/google/chrome/extensions",
                'for i in "${!EXTlist[@]}"; do',
                '  echo \'{"external_update_url": "https://clients2.google.com/service/update2/crx"}\' | sudo tee /opt/google/chrome/extensions/${EXTlist[$i]}.json > /dev/null',
                "done",
                'echo "Chrome extension installed. Restart Chrome and verify via chrome://extensions/"',
                ""
            );
        }
        // https://www.jetbrains.com/help/pycharm/install-plugins-from-the-command-line.html#linux
        // https://www.jetbrains.com/help/pycharm/working-with-the-ide-features-from-command-line.html#toolbox

        // Wrapper script
        const wrapperLines = [
            "# Auto start config",
            "cat > \"$WRAPPER_SCRIPT\" << 'EOF'",
            "#!/bin/bash",
            "set -e",
            "",
            'INSTALL_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/activitywatch"',
            'WATCHERS_DIR="$INSTALL_DIR/activitywatch"',
            'LOG_FILE="$INSTALL_DIR/startup.log"',
            "",
            'AW_AFK="$WATCHERS_DIR/aw-watcher-afk/aw-watcher-afk"',
            'AW_WINDOW="$WATCHERS_DIR/aw-watcher-window/aw-watcher-window"',
            'AW_SERVER="$WATCHERS_DIR/aw-server/aw-server"',
            "",
            'cd "$WATCHERS_DIR"',
            "",
            "# Start watchers in background, log output",
            '$AW_AFK >> "$LOG_FILE" 2>&1 &',
            '$AW_WINDOW >> "$LOG_FILE" 2>&1 &',
            `$AW_SERVER --cors-origins ${odooUrl} >> "$LOG_FILE" 2>&1 &`,
            "EOF",
            "",
            'chmod +x "$WRAPPER_SCRIPT"',
            '(crontab -l 2>/dev/null | grep -F "$WRAPPER_SCRIPT") || \\',
            '    (crontab -l 2>/dev/null; echo "@reboot /bin/bash $WRAPPER_SCRIPT") | crontab -',
            "",
            'echo "Watchers will now run on every reboot."',
            '/bin/bash "$WRAPPER_SCRIPT"',
            'echo "Starting watchers now..."',
        ];

        const scriptText = [...lines, ...wrapperLines].join("\n");
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
