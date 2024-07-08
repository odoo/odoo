#!/bin/bash

ADDONS_DIR="/jonas/odoo17/local-addons"

# Función para verificar repositorios git de forma recursiva
check_git_status() {
    local dir="$1"
    for item in "$dir"/*; do
        if [ -d "$item/.git" ]; then
            echo "Repository: $(basename "$item")"
            cd "$item" || exit
            git status
            echo "---------------------------"
        elif [ -d "$item" ]; then
            check_git_status "$item"
        fi
    done
}

# Verificar que la carpeta de addons existe
if [ -d "$ADDONS_DIR" ]; then
    check_git_status "$ADDONS_DIR"
fi
