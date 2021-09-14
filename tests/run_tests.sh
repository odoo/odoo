#!/usr/bin/env bash

set -e
set -u
set -o pipefail

function cleanup() {
  docker compose -f tests/docker-compose.yml down -v
}

trap cleanup EXIT

if [[ $# -ne 1 ]]; then
  echo "Usage: run_tests.sh modules_file"
  exit 1
fi

MODULES_FILE=$1

docker compose -f tests/docker-compose.yml up -d
docker compose -f tests/docker-compose.yml exec odoo poetry install --only testing --no-interaction --no-cache

echo "---*** Running Odoo tests at_install ***---"
docker compose -f tests/docker-compose.yml exec odoo ./odoo-bin -d test --addons-path=addons,odoo/addons \
  -i $(awk '{if (NR > 1) { printf "," } printf "%s", $1}' ${MODULES_FILE}) \
  --test-enable --test-tags=-post_install \
  --stop-after-init

echo "---*** Running Odoo tests post_install ***---"
docker compose -f tests/docker-compose.yml exec odoo ./odoo-bin -d test --addons-path=addons,odoo/addons \
  --test-enable --test-tags=$(awk '{if (NR > 1) { printf "," } printf "/%s", $1}' ${MODULES_FILE}),-at_install \
  --stop-after-init
docker compose -f tests/docker-compose.yml down -v

