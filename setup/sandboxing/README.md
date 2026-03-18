# Sandboxing AI Coding Assistants

We advise running AI coding assistants in a sandbox for better security and privacy.
These scripts and configurations allow you to run popular AI coding assistants with
filesystem isolation, so the assistant can only access the files it needs to work
on, and not your entire home directory.

Without sandboxing, the AI assistant has access to your entire home directory, including
SSH keys, GPG keys, browser profiles, credentials files, and any other secrets.
Sandboxing restricts the visible filesystem to only the directories the assistant
actually needs.

AI assistants are powerful tools that can execute code, read and write files, and access
the network. Running them without isolation can lead to accidental data leaks or malicious
code execution if the assistant is compromised. By using sandboxing, you can mitigate
these risks while still benefiting from the assistant's capabilities.

## Bubblewrap

These scripts use [bubblewrap](https://github.com/containers/bubblewrap) to run AI
coding assistants with filesystem isolation, no container runtime needed.

All functions of the assistant should work as normal, but the assistant will only see a
limited view of the filesystem. The assistant will be able to edit files in the Odoo
workspace and any other explicitly added directories, but won't be able to access files
outside of those areas. It will also be able to run Python and JavaScript tests.

### Prerequisites

Install bubblewrap with your package manager. For example, on Debian/Ubuntu:

```sh
sudo apt install bubblewrap
```

It is advised to copy the scripts `bwrap-claude.sh` and `bwrap-opencode.sh` to a
directory in your PATH (e.g. `~/.local/bin`).

Both scripts pre-mount the Odoo workspace directory. By default, it is defined to `~/src/odoo`,
meaning that the workspace should contain the directories `~/src/odoo/odoo`,
`~/src/odoo/enterprise` and any other Odoo-related directory (e.g. design-themes).

Override the default path with the environment variable `ODOO_BASE` (e.g.
`ODOO_BASE=~/my/odoo`).

Chrome, PostgreSQL, and the Odoo filestore are mounted opportunistically with
`bind-try` and silently skipped when absent.

### bwrap-opencode.sh

Sandbox wrapper for [Opencode](https://opencode.ai).

Install Opencode as recommended by the documentation:
```sh
curl -fsSL https://opencode.ai/install | bash
```

Then, launch the sandboxed Opencode:

```sh
# Odoo dirs are pre-mounted, so no args needed for basic usage
bwrap-opencode.sh [opencode args...]

# Mount extra directories beyond Odoo
bwrap-opencode.sh --add-dir ~/src/my-project [opencode args...]
```

`--add-dir` paths are bind-mounted read-write into the sandbox. Opencode does not
support `--add-dir` natively, so these flags are consumed by the wrapper and **not**
forwarded to the opencode binary.

No IDE integration. See the script header for the full sandbox layout.


### bwrap-claude.sh

Sandbox wrapper for [Claude Code](https://docs.anthropic.com/en/docs/claude-code).

Install Claude Code as recommended by the documentation:
```sh
curl -fsSL https://claude.ai/install.sh | bash
```

Then, launch the sandboxed Claude:

```sh
# Odoo dirs are pre-mounted, so no args needed for basic usage
bwrap-claude.sh [claude args...]

# Mount extra directories beyond Odoo
bwrap-claude.sh --add-dir ~/src/my-project [claude args...]
```

Each `--add-dir` path is bind-mounted read-write **and** passed to Claude's own
`--add-dir` flag, so Claude's tool access matches the sandbox boundary.

For a complete sandboxing with VSCode, configure the
[Claude Code VSCode extension](https://marketplace.visualstudio.com/items?itemName=anthropic.claude-code)
and change the VSCode Claude extension setting
`claudeCode.claudeProcessWrapper` to `bwrap-claude.sh`.

In order to connect VSCode and the sandboxed Claude, type `/ide` in the Claude CLI.
If VSCode is started, it should appear in the Claude CLI output.

See the script header for the full sandbox layout.

### Example: Running Odoo tests

Here is an example of prompt to run the CRM tests (Python and JavaScript tours):

```
Here is how to initialize a DB named "pouet" :
~/src/odoo/odoo/odoo-bin --addons-path=~/src/odoo/enterprise,~/src/odoo/odoo/addons -d pouet -i base --stop-after-init --logfile=~/src/odoo/log/pouet.log

Then, install the CRM module:
~/src/odoo/odoo/odoo-bin --addons-path=~/src/odoo/enterprise,~/src/odoo/odoo/addons -d pouet -i crm --stop-after-init --logfile=~/src/odoo/log/pouet.log

Finally, run the tests for the CRM module:
~/src/odoo/odoo/odoo-bin --addons-path=~/src/odoo/enterprise,~/src/odoo/odoo/addons -d pouet -u crm --test-enable --logfile=~/src/odoo/log/pouet.log

Can you do this for me?
```

You can follow the logs in the file `~/src/odoo/log/pouet.log`.
