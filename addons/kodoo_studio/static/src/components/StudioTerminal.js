/** @odoo-module ignore **/

odoo.define("kodoo_studio.StudioTerminal", ["kodoo_studio.forge_api"], function (require) {
    "use strict";

    const { Component, onMounted, onWillUnmount, onWillUpdateProps, useRef, useState } = owl;
    const forgeApi = require("kodoo_studio.forge_api");

    const namespace = window.kodooStudio = window.kodooStudio || {};
    namespace.components = namespace.components || {};
    if (!owl.registry) {
        owl.registry = {
            content: {},
            add(name, value) {
                this.content[name] = value;
                return value;
            },
            get(name) {
                return this.content[name];
            },
        };
    }

    class StudioTerminal extends Component {
        setup() {
            this.terminalRef = useRef("terminal");
            this.state = useState({
                status: "offline",
                message: "Waiting for terminal connection.",
            });

            this.commandBuffer = "";
            this.cwd = "";
            this.processRunning = false;
            this.socket = null;
            this.term = null;
            this.fitAddon = null;
            this.resizeObserver = null;
            this.reconnectTimer = null;
            this.reconnectAttempts = 0;
            this.tokenRetryUsed = false;
            this.manualClose = false;

            onMounted(() => this.mountTerminal());
            onWillUnmount(() => this.destroyTerminal());
            onWillUpdateProps((nextProps) => {
                if (nextProps.open && !this.props.open) {
                    this.fitSoon();
                }
            });
        }

        async mountTerminal() {
            const TerminalCtor = window.Terminal;
            const FitAddonCtor = window.FitAddon && window.FitAddon.FitAddon;
            if (!TerminalCtor) {
                this.state.status = "error";
                this.state.message = "xterm.js not available.";
                return;
            }

            this.term = new TerminalCtor({
                cursorBlink: true,
                convertEol: false,
                fontFamily: "'IBM Plex Mono', 'SFMono-Regular', Consolas, monospace",
                fontSize: 13,
                theme: {
                    background: "#1e1e1e",
                    foreground: "#d4d4d4",
                    cursor: "#f5f5f5",
                },
            });

            if (FitAddonCtor) {
                this.fitAddon = new FitAddonCtor();
                this.term.loadAddon(this.fitAddon);
            }

            this.term.open(this.terminalRef.el);
            this.fitSoon();
            this.term.onData((data) => this.handleInput(data));

            this.resizeObserver = new ResizeObserver(() => {
                if (!this.props.open) {
                    return;
                }
                this.fitSoon();
                this.sendResize();
            });
            this.resizeObserver.observe(this.terminalRef.el);

            await this.connectSocket();
        }

        async connectSocket(isReconnect) {
            if (this.manualClose) {
                return;
            }
            this.state.status = "connecting";
            this.state.message = isReconnect ? "Reconnecting..." : "Requesting terminal token...";

            let token;
            try {
                const tokenResult = await forgeApi.getTerminalToken();
                token = tokenResult && tokenResult.token ? tokenResult.token : null;
                if (!token) {
                    throw new Error("Missing terminal token.");
                }
            } catch (error) {
                this.state.status = "error";
                this.state.message = error.message || "Could not open terminal.";
                this.writeNotice("[Falha ao obter token do terminal.]");
                if (isReconnect) {
                    this.scheduleReconnect();
                }
                return;
            }

            const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
            this.socket = new window.WebSocket(
                `${protocol}//${window.location.host}/kodoo/studio/ws/terminal?token=${encodeURIComponent(token)}`
            );

            this.socket.onopen = () => {
                this.state.status = "connected";
                this.state.message = "Connected";
                this.reconnectAttempts = 0;
                this.tokenRetryUsed = false;
                this.sendResize();
            };

            this.socket.onmessage = (event) => {
                this.handleMessage(event.data);
            };

            this.socket.onerror = () => {
                this.state.message = "Terminal bridge error.";
            };

            this.socket.onclose = (event) => {
                this.handleSocketClose(event);
            };
        }

        handleSocketClose(event) {
            this.socket = null;
            this.processRunning = false;
            if (this.manualClose) {
                return;
            }
            if (event.code === 1000) {
                this.state.status = "closed";
                this.state.message = "Disconnected";
                this.writeNotice("[terminal] connection closed");
                return;
            }
            if (event.code === 4001 && !this.tokenRetryUsed) {
                this.tokenRetryUsed = true;
                this.state.status = "connecting";
                this.state.message = "Refreshing terminal token...";
                this.writeNotice("[Token expirado. Reconectando...]");
                this.connectSocket(true);
                return;
            }
            this.scheduleReconnect();
        }

        scheduleReconnect() {
            if (this.manualClose) {
                return;
            }
            if (this.reconnectAttempts >= 3) {
                this.state.status = "error";
                this.state.message = "Reconnect failed";
                this.writeNotice("[Falha ao reconectar. Abra e feche o terminal.]");
                return;
            }
            this.reconnectAttempts += 1;
            this.state.status = "connecting";
            this.state.message = `Reconnect attempt ${this.reconnectAttempts}/3`;
            this.writeNotice("[Conex\u00e3o perdida. Reconectando em 3s...]");
            if (this.reconnectTimer) {
                window.clearTimeout(this.reconnectTimer);
            }
            this.reconnectTimer = window.setTimeout(() => {
                this.reconnectTimer = null;
                this.connectSocket(true);
            }, 3000);
        }

        handleMessage(rawMessage) {
            let payload;
            try {
                payload = JSON.parse(rawMessage);
            } catch {
                this.term.write(rawMessage || "");
                return;
            }

            if (payload.type === "ready") {
                this.cwd = payload.cwd || "";
                this.writeSystem(`cwd=${this.cwd || "."}`);
                this.writePrompt();
                return;
            }
            if (payload.type === "output") {
                this.term.write(payload.data || "");
                return;
            }
            if (payload.type === "exit") {
                this.processRunning = false;
                this.term.write(`\r\n[Process exited: ${payload.code}]\r\n`);
                this.writePrompt();
                return;
            }
            if (payload.type === "error") {
                this.term.write(`\r\n[Error] ${payload.data || "Unknown error"}\r\n`);
                if (!this.processRunning) {
                    this.writePrompt();
                }
            }
        }

        handleInput(data) {
            if (!this.socket || this.socket.readyState !== window.WebSocket.OPEN) {
                return;
            }
            if (data === "\u0003") {
                this.term.write("^C");
                this.sendJson({ type: "signal", data: "SIGINT" });
                if (!this.processRunning) {
                    this.commandBuffer = "";
                    this.term.write("\r\n");
                    this.writePrompt();
                }
                return;
            }
            if (this.processRunning) {
                return;
            }
            if (data === "\r") {
                const command = this.commandBuffer;
                this.commandBuffer = "";
                this.term.write("\r\n");
                if (!command.trim()) {
                    this.writePrompt();
                    return;
                }
                this.processRunning = true;
                this.sendJson({ type: "input", data: command });
                return;
            }
            if (data === "\u007F") {
                if (this.commandBuffer.length) {
                    this.commandBuffer = this.commandBuffer.slice(0, -1);
                    this.term.write("\b \b");
                }
                return;
            }
            if (data >= " ") {
                this.commandBuffer += data;
                this.term.write(data);
            }
        }

        sendJson(payload) {
            if (this.socket && this.socket.readyState === window.WebSocket.OPEN) {
                this.socket.send(JSON.stringify(payload));
            }
        }

        sendResize() {
            if (!this.term || !this.props.open) {
                return;
            }
            this.sendJson({
                type: "resize",
                cols: this.term.cols,
                rows: this.term.rows,
            });
        }

        fitSoon() {
            window.setTimeout(() => {
                if (this.fitAddon && this.props.open) {
                    this.fitAddon.fit();
                }
            }, 0);
        }

        writePrompt() {
            if (!this.term) {
                return;
            }
            this.term.write(`${this.cwd || "."}$ `);
        }

        writeSystem(message) {
            if (!this.term) {
                return;
            }
            this.term.write(`${message}\r\n`);
        }

        writeNotice(message) {
            if (!this.term) {
                return;
            }
            this.term.write(`\r\n${message}\r\n`);
        }

        destroyTerminal() {
            this.manualClose = true;
            if (this.reconnectTimer) {
                window.clearTimeout(this.reconnectTimer);
                this.reconnectTimer = null;
            }
            if (this.resizeObserver) {
                this.resizeObserver.disconnect();
                this.resizeObserver = null;
            }
            if (this.socket) {
                this.socket.close(1000, "CLIENT_CLOSED");
                this.socket = null;
            }
            if (this.term) {
                this.term.dispose();
                this.term = null;
            }
            this.fitAddon = null;
        }
    }

    StudioTerminal.template = "StudioTerminal";
    namespace.components.StudioTerminal = StudioTerminal;
    owl.registry.add("StudioTerminal", StudioTerminal);
    return StudioTerminal;
});
