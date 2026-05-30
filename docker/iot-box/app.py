#!/usr/bin/env python3
"""
Minimal Odoo IoT Box — ESC/POS bridge for generic network printers.
Implements the Odoo hw_proxy HTTP API so Odoo POS can print receipts
and kitchen tickets to standard TCP:9100 ESC/POS printers.

Configuration is managed via the web UI at http://iot-box:8069/
and stored in /app/config/config.json (persisted via Docker volume).
"""
import os
import io
import json
import base64
import logging
import socket
import concurrent.futures
import xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image
from flask import Flask, request, jsonify, render_template_string

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s %(message)s")
log = logging.getLogger(__name__)

app = Flask(__name__)


CONFIG_FILE = Path("/app/config/config.json")
CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)

# ── Config helpers ────────────────────────────────────────────────────────────

def load_config():
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text())
        except Exception:
            pass
    return {
        "receipt_printer_ip":  os.getenv("RECEIPT_PRINTER_IP", ""),
        "kitchen_printer_ip":  os.getenv("KITCHEN_PRINTER_IP", ""),
        "printer_port":        int(os.getenv("PRINTER_PORT", "9100")),
        "printer_timeout":     int(os.getenv("PRINTER_TIMEOUT", "5")),
    }

def save_config(cfg):
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2))

# ── Printer helpers ───────────────────────────────────────────────────────────

def get_printer(ip, cfg):
    from escpos.printer import Network
    return Network(ip, port=cfg["printer_port"], timeout=cfg["printer_timeout"])

def printer_reachable(ip, port, timeout=3):
    if not ip:
        return False
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except Exception:
        return False


def scan_network_printers(subnet, port=9100, timeout=0.5):
    """Scan subnet (e.g. '192.168.50') for devices with port 9100 open."""
    def check(host):
        try:
            with socket.create_connection((host, port), timeout=timeout):
                try:
                    name = socket.gethostbyaddr(host)[0]
                except Exception:
                    name = ""
                return {"ip": host, "port": port, "name": name}
        except Exception:
            return None

    hosts = [f"{subnet}.{i}" for i in range(1, 255)]
    found = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as ex:
        for result in ex.map(check, hosts):
            if result:
                found.append(result)
    found.sort(key=lambda x: int(x["ip"].split(".")[-1]))
    return found


def detect_subnet():
    """Return LAN subnet from env var (set in docker-compose) or fall back to 192.168.1."""
    subnet = os.getenv("LAN_SUBNET", "").strip()
    if subnet:
        return subnet.rstrip(".")
    return "192.168.1"

def xml_to_escpos(printer, xml_str):
    try:
        root = ET.fromstring(xml_str)
    except ET.ParseError:
        printer.text(xml_str)
        printer.cut()
        return

    def process(node):
        tag  = (node.tag or "").lower()
        text = (node.text or "").strip()

        if tag == "receipt":
            for child in node: process(child)

        elif tag in ("line", "br"):
            left = right = ""
            for child in node:
                ctag = (child.tag or "").lower()
                if ctag == "left":   left  = (child.text or "").strip()
                elif ctag == "right": right = (child.text or "").strip()
                elif ctag == "value": left  = (child.text or "").strip()
            if right:
                printer.text(f"{left:<24}{right:>8}\n")
            elif left:
                printer.text(f"{left}\n")
            else:
                printer.text("\n")

        elif tag == "div":
            printer.text("-" * 32 + "\n")

        elif tag in ("h1", "h2", "title"):
            printer.set(align="center", bold=True, double_height=(tag == "h1"))
            if text: printer.text(text + "\n")
            for child in node: process(child)
            printer.set(align="left", bold=False, double_height=False)

        elif tag == "center":
            printer.set(align="center")
            if text: printer.text(text + "\n")
            for child in node: process(child)
            printer.set(align="left")

        elif tag == "b":
            printer.set(bold=True)
            if text: printer.text(text)
            for child in node: process(child)
            printer.set(bold=False)

        elif tag == "barcode":
            try:
                printer.barcode((node.text or "").strip(), node.get("encoding", "EAN13").upper())
            except Exception as e:
                log.warning(f"Barcode error: {e}")
        else:
            if text: printer.text(text + "\n")
            for child in node: process(child)

    process(root)
    printer.cut()

# ── Web config UI ─────────────────────────────────────────────────────────────

CONFIG_HTML = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>IoT Box — Printer Config</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
           background: #f4f6f9; display: flex; justify-content: center;
           padding: 40px 16px; }
    .card { background: white; border-radius: 12px; padding: 32px;
            width: 100%; max-width: 520px;
            box-shadow: 0 2px 12px rgba(0,0,0,.08); }
    h1 { font-size: 20px; color: #1a1a2e; margin-bottom: 6px; }
    .subtitle { color: #666; font-size: 14px; margin-bottom: 28px; }
    label { display: block; font-size: 13px; font-weight: 600;
            color: #444; margin-bottom: 6px; margin-top: 20px; }
    input[type=text], input[type=number] {
            width: 100%; padding: 10px 14px; border: 1px solid #ddd;
            border-radius: 8px; font-size: 15px; outline: none;
            transition: border .2s; }
    input:focus { border-color: #875a7b; }
    .status { display: inline-block; width: 10px; height: 10px;
              border-radius: 50%; margin-right: 6px; }
    .status.ok  { background: #28a745; }
    .status.err { background: #dc3545; }
    .status-row { font-size: 13px; color: #555; margin-top: 6px;
                  display: flex; align-items: center; }
    .btn { margin-top: 16px; width: 100%; padding: 12px;
           background: #875a7b; color: white; border: none;
           border-radius: 8px; font-size: 15px; font-weight: 600;
           cursor: pointer; transition: background .2s; }
    .btn:hover { background: #6d4a65; }
    .btn-scan { background: #6c757d; }
    .btn-scan:hover { background: #545b62; }
    .btn-test { background: #17a2b8; }
    .btn-test:hover { background: #138496; }
    .alert { padding: 10px 14px; border-radius: 8px; margin-top: 16px;
             font-size: 14px; display: none; }
    .alert.success { background: #d4edda; color: #155724; display: block; }
    .alert.error   { background: #f8d7da; color: #721c24; display: block; }
    .divider { border: none; border-top: 1px solid #eee; margin: 24px 0; }
    .scanner-results { margin-top: 16px; }
    .printer-row { display: flex; align-items: center; justify-content: space-between;
                   padding: 10px 12px; border: 1px solid #eee; border-radius: 8px;
                   margin-bottom: 8px; background: #fafafa; }
    .printer-info { font-size: 13px; }
    .printer-ip { font-weight: 600; color: #333; }
    .printer-name { color: #888; font-size: 12px; }
    .assign-btns { display: flex; gap: 6px; }
    .btn-assign { padding: 5px 10px; font-size: 12px; border: none;
                  border-radius: 6px; cursor: pointer; font-weight: 600; }
    .btn-receipt { background: #875a7b; color: white; }
    .btn-kitchen { background: #28a745; color: white; }
    .scanning-msg { text-align: center; color: #666; font-size: 14px;
                    padding: 16px; display: none; }
  </style>
</head>
<body>
<div class="card">
  <h1>🖨 IoT Box</h1>
  <p class="subtitle">ESC/POS Printer Configuration</p>

  {% if message %}
  <div class="alert {{ 'success' if success else 'error' }}">{{ message }}</div>
  {% endif %}

  <!-- Scanner -->
  <label>Scan Network for Printers</label>
  <div style="display:flex; gap:8px; margin-top:6px;">
    <input type="text" id="subnet" value="{{ subnet }}" placeholder="192.168.50" style="flex:1;">
    <button class="btn btn-scan" style="margin:0;width:auto;padding:10px 18px;"
            onclick="scanNetwork()">Scan</button>
  </div>
  <p class="scanning-msg" id="scanning-msg">⏳ Scanning network... (up to 15 seconds)</p>
  <div class="scanner-results" id="scan-results"></div>

  <hr class="divider">

  <!-- Manual config -->
  <form method="POST" action="/config">
    <label>Receipt Printer IP</label>
    <input type="text" name="receipt_printer_ip" id="receipt_ip"
           value="{{ cfg.receipt_printer_ip }}" placeholder="e.g. 192.168.50.124">
    <div class="status-row">
      <span class="status {{ 'ok' if receipt_ok else 'err' }}"></span>
      {{ 'Reachable' if receipt_ok else 'Not reachable' }}
    </div>

    <label>Kitchen Printer IP</label>
    <input type="text" name="kitchen_printer_ip" id="kitchen_ip"
           value="{{ cfg.kitchen_printer_ip }}" placeholder="e.g. 192.168.50.125">
    <div class="status-row">
      <span class="status {{ 'ok' if kitchen_ok else 'err' }}"></span>
      {{ 'Reachable' if kitchen_ok else 'Not reachable' }}
    </div>

    <label>Printer Port</label>
    <input type="number" name="printer_port" value="{{ cfg.printer_port }}" placeholder="9100">

    <button class="btn" type="submit">Save Configuration</button>
  </form>

  <form method="POST" action="/test_print">
    <button class="btn btn-test" type="submit">Test Print (Receipt Printer)</button>
  </form>
</div>

<script>
function scanNetwork() {
  const subnet = document.getElementById('subnet').value.trim();
  document.getElementById('scanning-msg').style.display = 'block';
  document.getElementById('scan-results').innerHTML = '';
  fetch('/scan?subnet=' + encodeURIComponent(subnet))
    .then(r => r.json())
    .then(data => {
      document.getElementById('scanning-msg').style.display = 'none';
      const el = document.getElementById('scan-results');
      if (!data.length) {
        el.innerHTML = '<p style="color:#888;font-size:13px;margin-top:8px;">No printers found on ' + subnet + '.0/24</p>';
        return;
      }
      el.innerHTML = data.map(p => `
        <div class="printer-row">
          <div class="printer-info">
            <div class="printer-ip">${p.ip}</div>
            <div class="printer-name">${p.name || 'Generic ESC/POS Printer'} &nbsp;·&nbsp; port ${p.port}</div>
          </div>
          <div class="assign-btns">
            <button class="btn-assign btn-receipt" onclick="assign('receipt','${p.ip}')">Receipt</button>
            <button class="btn-assign btn-kitchen" onclick="assign('kitchen','${p.ip}')">Kitchen</button>
          </div>
        </div>`).join('');
    })
    .catch(() => {
      document.getElementById('scanning-msg').style.display = 'none';
      document.getElementById('scan-results').innerHTML = '<p style="color:red;font-size:13px;">Scan failed.</p>';
    });
}

function assign(type, ip) {
  if (type === 'receipt') document.getElementById('receipt_ip').value = ip;
  else document.getElementById('kitchen_ip').value = ip;
}
</script>
</body>
</html>
"""

@app.route("/", methods=["GET"])
def config_page():
    cfg        = load_config()
    receipt_ok = printer_reachable(cfg["receipt_printer_ip"], cfg["printer_port"])
    kitchen_ok = printer_reachable(cfg["kitchen_printer_ip"], cfg["printer_port"])
    return render_template_string(CONFIG_HTML, cfg=cfg,
                                  receipt_ok=receipt_ok, kitchen_ok=kitchen_ok,
                                  subnet=detect_subnet(),
                                  message=None, success=False)


@app.route("/scan")
def scan():
    subnet  = request.args.get("subnet", detect_subnet()).strip()
    port    = load_config().get("printer_port", 9100)
    log.info(f"Scanning {subnet}.0/24 for port {port}...")
    results = scan_network_printers(subnet, port=port)
    log.info(f"Found {len(results)} printer(s)")
    return jsonify(results)

@app.route("/config", methods=["POST"])
def save_config_route():
    cfg = load_config()
    cfg["receipt_printer_ip"] = request.form.get("receipt_printer_ip", "").strip()
    cfg["kitchen_printer_ip"] = request.form.get("kitchen_printer_ip", "").strip()
    cfg["printer_port"]       = int(request.form.get("printer_port", 9100) or 9100)
    save_config(cfg)
    log.info(f"Config saved: receipt={cfg['receipt_printer_ip']} kitchen={cfg['kitchen_printer_ip']}")
    receipt_ok = printer_reachable(cfg["receipt_printer_ip"], cfg["printer_port"])
    kitchen_ok = printer_reachable(cfg["kitchen_printer_ip"], cfg["printer_port"])
    return render_template_string(CONFIG_HTML, cfg=cfg,
                                  receipt_ok=receipt_ok, kitchen_ok=kitchen_ok,
                                  subnet=detect_subnet(),
                                  message="Configuration saved.", success=True)

@app.route("/test_print", methods=["POST"])
def test_print_route():
    cfg = load_config()
    ip  = cfg["receipt_printer_ip"]
    if not ip:
        receipt_ok = kitchen_ok = False
        return render_template_string(CONFIG_HTML, cfg=cfg,
                                      receipt_ok=receipt_ok, kitchen_ok=kitchen_ok,
                                      subnet=detect_subnet(),
                                      message="No receipt printer IP configured.", success=False)
    try:
        printer = get_printer(ip, cfg)
        printer.set(align="center", bold=True)
        printer.text("=== TEST PRINT ===\n")
        printer.set(align="left", bold=False)
        printer.text(f"Receipt: {ip}:{cfg['printer_port']}\n")
        printer.text("ESC/POS connection OK\n")
        printer.cut()
        msg, ok = "Test print sent successfully.", True
    except Exception as e:
        msg, ok = f"Print failed: {e}", False
    receipt_ok = printer_reachable(cfg["receipt_printer_ip"], cfg["printer_port"])
    kitchen_ok = printer_reachable(cfg["kitchen_printer_ip"], cfg["printer_port"])
    return render_template_string(CONFIG_HTML, cfg=cfg,
                                  receipt_ok=receipt_ok, kitchen_ok=kitchen_ok,
                                  subnet=detect_subnet(),
                                  message=msg, success=ok)

# ── Odoo hw_proxy API ─────────────────────────────────────────────────────────

@app.route("/hw_proxy/hello")
def hello():
    return "ping"

@app.route("/hw_proxy/status_json", methods=["GET", "POST", "OPTIONS"])
def status():
    cfg    = load_config()
    port   = cfg["printer_port"]
    data   = request.get_json(silent=True) or {}
    req_id = data.get("id", 1)
    ok     = printer_reachable(cfg["receipt_printer_ip"], port) if cfg["receipt_printer_ip"] else False
    # Odoo's rpc() extracts response.result as `drivers` — must be JSON-RPC format
    return jsonify({
        "jsonrpc": "2.0",
        "id": req_id,
        "result": {
            "scanner": None,
            "scale":   None,
            "printer": {"status": "connected" if ok else "disconnected"}
        }
    })

@app.route("/hw_proxy/print_xml_receipt", methods=["POST", "GET"])
def print_receipt():
    cfg = load_config()
    if not cfg["receipt_printer_ip"]:
        return jsonify({"status": "error", "message": "Receipt printer IP not configured"}), 500
    try:
        data = request.get_json(silent=True) or {}
        log.info(f"Receipt print → {cfg['receipt_printer_ip']}")
        xml_to_escpos(get_printer(cfg["receipt_printer_ip"], cfg), data.get("receipt", ""))
        return jsonify({"status": "ok"})
    except Exception as e:
        log.error(f"Receipt print error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/hw_proxy/print_xml_order", methods=["POST", "GET"])
def print_order():
    cfg       = load_config()
    target_ip = cfg["kitchen_printer_ip"] or cfg["receipt_printer_ip"]
    if not target_ip:
        return jsonify({"status": "error", "message": "No printer configured"}), 500
    try:
        data = request.get_json(silent=True) or {}
        log.info(f"Kitchen print → {target_ip}")
        xml_to_escpos(get_printer(target_ip, cfg),
                      data.get("order", data.get("receipt", "")))
        return jsonify({"status": "ok"})
    except Exception as e:
        log.error(f"Kitchen print error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/hw_proxy/handshake", methods=["GET", "POST", "OPTIONS"])
def handshake():
    data  = request.get_json(silent=True) or {}
    return jsonify({"id": data.get("id", 1), "jsonrpc": "2.0", "result": {"status": "connected"}})


@app.route("/hw_proxy/default_printer_action", methods=["GET", "POST", "OPTIONS"])
def default_printer_action():
    cfg      = load_config()
    data     = request.get_json(silent=True) or {}
    req_id   = data.get("id", 1)
    params   = data.get("params", {})
    pdata    = params.get("data", {})
    img_b64  = pdata.get("receipt", "")

    if not img_b64:
        return jsonify({"id": req_id, "jsonrpc": "2.0",
                        "result": {"status": "error", "message": "No receipt data"}})

    caller     = request.remote_addr or ""
    user_agent = request.headers.get("User-Agent", "").lower()
    is_server  = "python" in user_agent or "odoo" in user_agent
    printer_type = "KITCHEN" if is_server else "RECEIPT"
    target_ip = (cfg["kitchen_printer_ip"] or cfg["receipt_printer_ip"]) if is_server \
                else cfg["receipt_printer_ip"]

    log.info(f"[{printer_type}] Print request from {caller} (ua: {user_agent[:40]}) → {target_ip}")

    printer = None
    try:
        img = Image.open(io.BytesIO(base64.b64decode(img_b64)))
        printer = get_printer(target_ip, cfg)
        printer.image(img, impl="bitImageRaster", center=True)
        printer.cut()
        log.info(f"[{printer_type}] Print OK")
        return jsonify({"id": req_id, "jsonrpc": "2.0", "result": {"status": "ok"}})
    except Exception as e:
        log.error(f"[{printer_type}] Print error: {e}")
        return jsonify({"id": req_id, "jsonrpc": "2.0",
                        "result": {"status": "error", "message": str(e)}})
    finally:
        if printer:
            try:
                printer.close()
            except Exception:
                pass


@app.route("/<path:path>", methods=["GET", "POST", "PUT", "DELETE"])
def catch_all(path):
    body = request.get_data(as_text=True)[:500]
    log.info(f"UNKNOWN REQUEST: {request.method} /{path} | body: {body}")
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    cfg = load_config()
    log.info(f"IoT Box starting — Receipt: {cfg['receipt_printer_ip']}, Kitchen: {cfg['kitchen_printer_ip']}")
    log.info("Config UI available at http://0.0.0.0:8069/")
    app.run(host="0.0.0.0", port=8069, debug=False)
