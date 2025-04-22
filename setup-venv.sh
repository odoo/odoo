#!/bin/bash

# Script to set up a Python virtual environment for Odoo
# Includes PostgreSQL dev libs, VSCode settings, and excludes venv from git

set -e

echo "🔍 Checking for Python 3..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Install it with: sudo apt install python3"
    exit 1
fi

echo "🔍 Checking for PostgreSQL dev libraries..."
if ! dpkg -l | grep libpq-dev &> /dev/null; then
    echo "⚡ Installing PostgreSQL development libraries..."
    sudo apt update
    sudo apt install -y libpq-dev
else
    echo "✅ PostgreSQL dev libs already installed."
fi

echo "📁 Creating virtual environment in ./venv"
python3 -m venv venv

echo "✅ Virtual environment created."

echo "⚡ Activating virtual environment..."
source venv/bin/activate

echo "⬆️ Upgrading pip and wheel..."
pip install --upgrade pip wheel

if [ -f requirements.txt ]; then
    echo "📦 Installing dependencies from requirements.txt..."
    pip install -r requirements.txt
else
    echo "⚠️ No requirements.txt found. You may need to install packages manually."
fi

echo "✅ All dependencies installed."

# Creating .vscode/settings.json for Python
echo "🔧 Setting up VSCode settings..."

mkdir -p .vscode
cat <<EOF > .vscode/settings.json
{
    "python.pythonPath": "venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": true,
    "python.formatting.autopep8Path": "venv/bin/autopep8",
    "python.formatting.blackPath": "venv/bin/black",
    "python.testing.pytestEnabled": true,
    "python.testing.pytestPath": "venv/bin/pytest"
}
EOF

echo "✅ VSCode settings added."

# Adding venv to .gitignore
echo "📂 Updating .gitignore to exclude venv/"

if [ ! -f .gitignore ]; then
    touch .gitignore
fi

# Add venv/ folder to .gitignore
echo "venv/" >> .gitignore

echo "✅ .gitignore updated to exclude venv/"

echo "🎉 Setup complete!"
echo "Your virtual environment is ready. To activate it again, run: source venv/bin/activate"
echo "VSCode settings have been configured. Open the project in VSCode."
