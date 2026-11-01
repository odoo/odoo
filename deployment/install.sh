#!/usr/bin/env bash
# ============================================================================
#  Odoo 19 CE Enterprise (AutoInfo) — Linux bootstrap
#  ติดตั้งจาก tag ที่ปล่อยจริง เสมอ (ห้าม deploy จาก branch tip)
#
#  ใช้งาน:
#     OD19_TAG=v19.0.0 OD19_REPO=https://github.com/nattanonvs/odoo19ce-autoinfo.git \
#       bash deployment/install.sh /opt/odoo19
# ============================================================================
set -euo pipefail

TARGET="${1:-/opt/odoo19}"
OD19_REPO="${OD19_REPO:?set OD19_REPO (repo url)}"
OD19_TAG="${OD19_TAG:?set OD19_TAG (release tag, e.g. v19.0.0)}"

echo "==> [1/6] clone ${OD19_REPO} @ ${OD19_TAG} -> ${TARGET}"
if [ -d "${TARGET}/.git" ]; then
  git -C "${TARGET}" fetch --tags --prune
else
  git clone --recurse-submodules "${OD19_REPO}" "${TARGET}"
fi

echo "==> [2/6] checkout tag + ยืนยัน submodules ตรงตามที่ pin ไว้"
git -C "${TARGET}" checkout "${OD19_TAG}"
git -C "${TARGET}" submodule update --init --recursive
git -C "${TARGET}" submodule status

echo "==> [3/6] สร้าง virtualenv"
python3 -m venv "${TARGET}/venv"
# shellcheck disable=SC1091
source "${TARGET}/venv/bin/activate"
python -m pip install --upgrade pip wheel

echo "==> [4/6] ติดตั้ง Python dependencies"
# (ก) Odoo core ก่อน — ล็อกรุ่น cryptography 42.0.8 / pyopenssl 24.1.0 ไว้
python -m pip install -r "${TARGET}/requirements.txt"
# (ข) แพ็กเกจที่โปรเจกต์เพิ่มเอง (ดู requirements-od19.txt)
python -m pip install \
  sentry-sdk==2.22.0 paramiko==3.5.1 pysftp==0.2.9 Pygments==2.21.0 \
  pdfminer.six==20260107 packaging==26.3 pikepdf==10.17.0 fonttools==4.60.1
# (ค) signxml ต้องใช้ --no-deps เท่านั้น
#     signxml 5.2.0 ประกาศ cryptography>=45 ซึ่งชนกับ core (42.0.8) -> ห้ามให้ pip resolve
python -m pip install --no-deps signxml==5.2.0
# หมายเหตุ: `pip check` จะรายงาน 2 ข้อที่ยอมรับได้ (signxml/cryptography, lxml) — ดู requirements-od19.txt

echo "==> [5/6] เตรียม config + โฟลเดอร์ข้อมูล"
install -d /etc/odoo /var/log/odoo /var/lib/odoo/data
if [ ! -f /etc/odoo/odoo19.conf ]; then
  cp "${TARGET}/deployment/odoo.conf.template" /etc/odoo/odoo19.conf
  echo "    !! แก้ค่า __SET_ME__ และ dbfilter ใน /etc/odoo/odoo19.conf ก่อนสตาร์ท"
fi

echo "==> [6/6] เสร็จ — ขั้นตอนถัดไป"
cat <<'EOF'
  - แก้ /etc/odoo/odoo19.conf  (admin_passwd, db_password, dbfilter, sentry_dsn)
  - sudo cp /opt/odoo19/deployment/systemd/odoo19.service /etc/systemd/system/
  - sudo systemctl daemon-reload && sudo systemctl enable --now odoo19
  - ตรวจ log: journalctl -u odoo19 -f
EOF
