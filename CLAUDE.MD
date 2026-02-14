# Odoo Development Guide

## Project Overview

This is an **Odoo** repository - a suite of open source business applications including CRM, eCommerce, Warehouse Management, Accounting, and more. The project is written primarily in Python with JavaScript for frontend components.

**Git Remote:** http://local_proxy@127.0.0.1:32827/git/psyberpunk/odoo

## Directory Structure

- **`addons/`** - Contains all Odoo modules and applications
- **`odoo/`** - Core Odoo framework and engine code
- **`doc/`** - Documentation
- **`.github/`** - GitHub workflows and CI/CD configuration
- **`odoo-bin`** - Main executable entry point
- **`requirements.txt`** - Python dependencies
- **`ruff.toml`** - Ruff linter configuration

## Development Workflow

### Branch Convention
- Always develop on assigned feature branches (e.g., `claude/update-claude-md-7CHry`)
- Branch names should start with `claude/` and include a session identifier
- Never push to main/master without explicit permission

### Setting Up Development Environment

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run Odoo server:**
   ```bash
   ./odoo-bin
   ```

### Code Quality

- **Linter:** Ruff is configured via `ruff.toml`
- **Code Style:** Follow PEP 8 standards
- **Testing:** Check module tests in respective addon directories

## Key Commands

| Command | Purpose |
|---------|---------|
| `./odoo-bin` | Start the Odoo server |
| `./odoo-bin -d <dbname>` | Start Odoo with specific database |
| `./odoo-bin --help` | Show all available options |
| `git push -u origin <branch-name>` | Push changes to feature branch |

## Module Development

Odoo modules typically contain:
- `__manifest__.py` - Module metadata and dependencies
- `models/` - Data models
- `views/` - UI definitions (XML)
- `controllers/` - Routes and web controllers
- `static/` - CSS, JS, and images
- `tests/` - Unit and integration tests

## Git Workflow

### Committing Changes
1. Make changes on your feature branch
2. Stage files: `git add <files>`
3. Commit with descriptive message: `git commit -m "Description"`
4. Push to remote: `git push -u origin <branch-name>`

### Important Notes
- All development must be on the designated feature branch
- Push failures with HTTP 403 indicate incorrect branch naming (must start with `claude/`)
- If network errors occur, retry push with exponential backoff

## Testing

- Addons may contain tests in their respective directories
- Run tests within Odoo using the `-i` and `--test-enable` flags:
  ```bash
  ./odoo-bin -i <addon_name> --test-enable -d <dbname>
  ```

## Resources

- [Odoo Documentation](https://www.odoo.com/documentation/master)
- [Odoo Developer Documentation](https://www.odoo.com/documentation/master/developer)
- [Contributing Guidelines](./CONTRIBUTING.md)
- [Security Policy](./SECURITY.md)

---

**Last Updated:** 2026-02-14
