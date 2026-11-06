# Project Rules & Agent Instructions

## Git & Deployment Rules
1. **NO AUTO PUSH**:
   - **NEVER** run `git push` automatically or proactively under any circumstances.
   - All changes must be developed, tested, and validated locally first.
   - Only execute `git push` when the user explicitly provides a direct command or instruction to push to remote.

2. **Security & Credentials**:
   - **NEVER** commit or push `.conf` files (`odoo.conf`, `odoo_local.conf`), `.env` files, production database passwords, connection strings, or database dumps (`*.dump`, `*.sql`).
   - Maintain these files in `.gitignore` and `.dockerignore`.

3. **Codebase & Architecture Standards**:
   - Never modify core Odoo files under `odoo/addons/` or `odoo/`.
   - All custom university functionality belongs in `custom/` (`custom/school_management`, `custom/school_website`, etc.).
   - When defining models, views, and reports, ensure XML manifest loading order respects dependencies (e.g., reports and actions must be loaded before email templates or views that reference their XML IDs).
