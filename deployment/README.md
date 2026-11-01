# Deployment — Odoo 19 CE Enterprise (AutoInfo)

ชุดไฟล์สำหรับนำ repo นี้ไปติดตั้งบนเซิร์ฟเวอร์อื่น (Linux) **จาก release tag เท่านั้น**

| ไฟล์ | หน้าที่ |
|---|---|
| `odoo.conf.template` | template คอนฟิก (sanitized — ไม่มี secret) |
| `systemd/odoo19.service` | systemd unit |
| `install.sh` | bootstrap: clone → checkout tag → submodule → venv → pip → config |

## หลักการ

- **Deploy จาก tag** (`v19.0.x`) ห้ามใช้ branch tip
- **Submodule ต้องตรงตามที่ pin** ใน commit ของ tag (`git submodule status` ต้องไม่มี `+`/`-`)
- **ห้ามฝัง secret** ในไฟล์ที่ commit (admin_passwd, db_password, sentry_dsn) — ใส่ที่ `/etc/odoo/odoo19.conf` บนเครื่องนั้น
- `addons_path` ลำดับ: core (`addons`, `odoo/addons`) → OCA (`third_party/oca/*`) → `custom_addons`

## ขั้นตอนติดตั้ง (ย่อ)

```bash
OD19_REPO=https://github.com/nattanonvs/odoo19ce-autoinfo.git \
OD19_TAG=v19.0.0 \
  bash deployment/install.sh /opt/odoo19

sudo cp /opt/odoo19/deployment/systemd/odoo19.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now odoo19
```

จากนั้นวาง reverse proxy (nginx) ชี้ไปที่ `127.0.0.1:8069` และตั้ง `proxy_mode = True` (มีใน template แล้ว)

## ติดตั้งโมดูลโปรเจกต์

เมื่อมี DB แล้ว ให้ติดตั้งชุดโมดูล `od19_*` ตามลำดับ dependency:

```bash
cd /opt/odoo19 && source venv/bin/activate
python odoo-bin -c /etc/odoo/odoo19.conf -d __DB__ -i od19_thai_localization_base --stop-after-init
```

> รายการโมดูลและลำดับ dependency ดูที่ `docs/superpowers/programs/odoo19-enterprise/`

## อัปเกรดจาก upstream (บนเครื่อง dev เท่านั้น)

```bash
git fetch upstream
git checkout 19.0
git merge upstream/19.0        # path ของ core ไม่ทับกับงานเรา
# ทดสอบ -> tag ใหม่ v19.0.<n> -> push ขึ้น origin
```

## Rollback

```bash
git checkout v19.0.<n-1>
git submodule update --init --recursive
sudo systemctl restart odoo19
```

## หมายเหตุ

- พอร์ต default 8069 (http) / 8072 (gevent) — ปรับใน config ได้
- `workers = 9` ใน template เป็นตัวอย่างสำหรับ 4 vCPU; ปรับตามเครื่อง (`2*CPU+1`)
- wkhtmltopdf ต้องติดตั้งในเครื่อง (ใช้สร้าง PDF report) — ไม่ได้อยู่ใน repo
