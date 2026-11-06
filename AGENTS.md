# Project Rules & Agent Instructions

## 0. Mandatory First Step
- **ALWAYS READ AGENTS.md FIRST**:
  - Before starting any task, debugging an issue, fixing an error, or touching any code, the agent **MUST** read this file (`AGENTS.md`) first to adhere to all project rules, constraints, and standards.

## 1. Git & Deployment Rules
1. **NO AUTO COMMIT**:
   - **NEVER** run `git commit` automatically without explicit user instruction.
   - Keep all changes uncommitted in the working tree until the user asks you to commit.

2. **PROVIDE COMMIT MESSAGE ONLY UPON COMPLETION**:
   - When a task, feature build, or error fix is completed and verified, do **NOT** commit or push.
   - Instead, provide **ONLY the recommended commit command and message** (formatted following conventional commit standards) so the user can review and commit at their own discretion.

3. **NO `git add .`**:
   - **NEVER** use broad staging commands like `git add .`, `git add -A`, or `git commit -a`.
   - Never stage unintended files or untracked assets.
   - If staging is requested, only specify or stage individual, explicitly targeted files (e.g. `git add path/to/specific_file.py`).

4. **NO AUTO PUSH**:
   - **NEVER** run `git push` automatically or proactively under any circumstances.
   - Only execute `git push` when the user explicitly instructs you to push.

5. **Security & Credentials**:
   - **NEVER** commit or push `.conf` files (`odoo.conf`, `odoo_local.conf`), `.env` files, production database passwords, connection strings, or database dumps (`*.dump`, `*.sql`).
   - Maintain these files in `.gitignore` and `.dockerignore`.

## 2. Codebase & Architecture Standards
1. **Custom Addons Only**:
   - Never modify core Odoo files under `odoo/addons/` or `odoo/`.
   - All custom university functionality belongs in `custom/` (`custom/school_management`, `custom/school_website`, etc.).

2. **Manifest Loading Order**:
   - When defining models, views, and reports, ensure XML manifest loading order respects dependencies (e.g., reports and actions must be loaded before email templates or views that reference their XML IDs).
