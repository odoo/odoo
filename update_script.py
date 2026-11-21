#!/usr/bin/env python3
"""
University Management System - Odoo Module Upgrade Script
Executes Odoo upgrade with configuration in C:/Odoo/odoo/odoo.conf
"""
import os
import subprocess
import sys

BASE_DIR = r"C:\Odoo\odoo"
PYTHON_EXE = os.path.join(BASE_DIR, "venv", "Scripts", "python.exe")
ODOO_BIN = os.path.join(BASE_DIR, "odoo-bin")
ODOO_CONF = os.path.join(BASE_DIR, "odoo.conf")
MODULE_NAME = "school_management"
DB_NAME = "odoo"


def run_upgrade():
    if not os.path.exists(PYTHON_EXE):
        print(f"Error: Python executable not found at {PYTHON_EXE}")
        sys.exit(1)
    if not os.path.exists(ODOO_BIN):
        print(f"Error: odoo-bin not found at {ODOO_BIN}")
        sys.exit(1)
    if not os.path.exists(ODOO_CONF):
        print(f"Error: odoo.conf not found at {ODOO_CONF}")
        sys.exit(1)

    cmd = [
        PYTHON_EXE,
        ODOO_BIN,
        "-c",
        ODOO_CONF,
        "-u",
        MODULE_NAME,
        "-d",
        DB_NAME,
        "--stop-after-init",
    ]

    print(f"Running command: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=BASE_DIR)
    if result.returncode == 0:
        print("\n[SUCCESS] Module updated successfully!")
    else:
        print(f"\n[FAILURE] Module update failed with exit code {result.returncode}")
    sys.exit(result.returncode)


if __name__ == "__main__":
    run_upgrade()
